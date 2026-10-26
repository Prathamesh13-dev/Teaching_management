from app.database import SessionLocal
from app import models
from app.routers import auth, materials, assignments, announcements, attendance, chat, whiteboard, admin, courses
from fastapi import HTTPException

def test_full_system_suite():
    print("[*] Running comprehensive API & domain test suite...")
    db = SessionLocal()
    test_course_id = None
    try:
        student = db.query(models.User).filter(models.User.username == "student_demo").first()
        teacher = db.query(models.User).filter(models.User.username == "teacher_demo").first()
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()

        assert student is not None, "student_demo not found"
        assert teacher is not None, "teacher_demo not found"
        assert admin_user is not None, "admin not found"
        print("  [OK] User entities and roles verified")

        for privileged_role in ("teacher", "admin"):
            try:
                auth.create_user(
                    auth.UserCreate(
                        username=f"self_registered_{privileged_role}",
                        password="test-password",
                        role=privileged_role
                    ),
                    db=db
                )
                assert False, f"Public registration must reject {privileged_role} accounts"
            except HTTPException as exc:
                assert exc.status_code == 403
        print("  [OK] Public registration cannot self-assign privileged roles")

        # Materials check
        mats = materials.get_materials(subject=None, db=db, current_user=student)
        assert len(mats) >= 2
        print(f"  [OK] Materials retrieved: {len(mats)} documents")

        # Assignments check
        assgns = assignments.get_assignments(subject=None, db=db, current_user=student)
        assert len(assgns) >= 2
        print(f"  [OK] Assignments retrieved: {len(assgns)} active assignments")

        # Attendance check
        att = attendance.get_student_attendance(db=db, current_user=student)
        assert att["total_sessions"] >= 5
        print(f"  [OK] Student attendance percentage: {att['percentage']}%")

        # Announcements check
        ann = announcements.get_announcements(db=db, current_user=student)
        assert len(ann) >= 2
        print(f"  [OK] Announcements feed verified: {len(ann)} notices")

        # Whiteboard check
        wb = whiteboard.get_saved_lessons(subject=None, db=db, current_user=student)
        assert len(wb) >= 1
        print(f"  [OK] Whiteboard lesson library verified: {len(wb)} saved boards")

        # Chat check
        groups = chat.get_groups(db=db, current_user=student)
        assert len(groups) >= 1
        print(f"  [OK] Study groups verified: {len(groups)} group(s)")

        # Admin stats check
        stats = admin.get_system_stats(db=db, current_user=admin_user)
        assert stats["users"]["total"] >= 5
        print(f"  [OK] Admin governance statistics verified: {stats['users']['total']} total users")

        # Teacher creates a class and students enroll using its generated join code
        created = courses.create_course(
            courses.CourseCreate(
                name="Class code enrollment test",
                code="TEST-LABEL-ONLY",
                section="Test Section"
            ),
            db=db,
            current_user=teacher
        )
        test_course_id = created["id"]
        assert len(created["join_code"]) == 6
        teacher_classes = courses.get_my_classes(db=db, current_user=teacher)
        listed_class = next(c for c in teacher_classes if c["id"] == test_course_id)
        assert listed_class["join_code"] == created["join_code"]

        catalog = courses.get_available_classes(db=db, current_user=student)
        catalog_class = next(c for c in catalog if c["id"] == test_course_id)
        assert "join_code" not in catalog_class
        try:
            courses.get_course_details(test_course_id, db=db, current_user=student)
            assert False, "A student must not view a class before enrolling"
        except HTTPException as exc:
            assert exc.status_code == 403

        joined = courses.join_class_by_code(
            courses.JoinCodeRequest(code=created["join_code"].upper()),
            db=db,
            current_user=student
        )
        assert joined["course_id"] == test_course_id
        assert courses.get_course_details(
            test_course_id, db=db, current_user=student
        )["join_code"] is None
        try:
            courses.join_class_by_code(
                courses.JoinCodeRequest(code="TEST-LABEL-ONLY"),
                db=db,
                current_user=student
            )
            assert False, "A course label must not work as a class join code"
        except HTTPException as exc:
            assert exc.status_code == 404
        try:
            courses.join_class_by_code(
                courses.JoinCodeRequest(code=created["join_code"]),
                db=db,
                current_user=teacher
            )
            assert False, "Teachers must not enroll through the student join endpoint"
        except HTTPException as exc:
            assert exc.status_code == 403
        print("  [OK] Teacher class-code creation, sharing, and student enrollment verified")

        print("[SUCCESS] All system validation tests passed!")

    finally:
        if test_course_id is not None:
            test_course = db.query(models.Course).filter(models.Course.id == test_course_id).first()
            if test_course:
                db.delete(test_course)
                db.commit()
        db.close()

if __name__ == "__main__":
    test_full_system_suite()
