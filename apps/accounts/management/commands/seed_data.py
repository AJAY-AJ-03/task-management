import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.attendance.models import Attendance, AttendanceStatus
from apps.breaks.models import BreakType
from apps.employees.models import EmployeeProfile, EmployeeStatus
from apps.leave.models import LeaveBalance, LeaveType
from apps.organization.models import Department, Process, Team
from apps.performance.models import KPI, KPITargetType, PerformanceRecord
from apps.shifts.models import EmployeeShift, Shift
from apps.tasks.models import Task, TaskPriority, TaskStatus


class Command(BaseCommand):
    help = "Seed database with realistic initial demo data for BPO Operations Management System V1."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Seeding demo data..."))

        # 1. Super Admin
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@bpo.com",
                "first_name": "Super",
                "last_name": "Admin",
                "role": Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "employee_id": "ADM001",
            },
        )
        admin.set_password("AdminPassword123!")
        admin.save()

        # 2. Manager
        manager, _ = User.objects.get_or_create(
            username="manager1",
            defaults={
                "email": "manager1@bpo.com",
                "first_name": "Sarah",
                "last_name": "Connor",
                "role": Role.MANAGER,
                "is_staff": True,
                "employee_id": "MGR001",
            },
        )
        manager.set_password("ManagerPassword123!")
        manager.save()

        # 3. Team Leaders
        tl1, _ = User.objects.get_or_create(
            username="tl1",
            defaults={
                "email": "tl1@bpo.com",
                "first_name": "John",
                "last_name": "Leader",
                "role": Role.TEAM_LEADER,
                "employee_id": "TL001",
            },
        )
        tl1.set_password("TLPassword123!")
        tl1.save()

        tl2, _ = User.objects.get_or_create(
            username="tl2",
            defaults={
                "email": "tl2@bpo.com",
                "first_name": "Jane",
                "last_name": "Supervisor",
                "role": Role.TEAM_LEADER,
                "employee_id": "TL002",
            },
        )
        tl2.set_password("TLPassword123!")
        tl2.save()

        # 4. Departments & Processes
        dept1, _ = Department.objects.get_or_create(name="Customer Support", description="Handling inbound customer calls and emails.")
        dept2, _ = Department.objects.get_or_create(name="Technical Support", description="Tier 1 and 2 technical support.")

        proc1, _ = Process.objects.get_or_create(department=dept1, name="Voice Support", description="Inbound Voice Process")
        proc2, _ = Process.objects.get_or_create(department=dept1, name="Email Support", description="Customer Email Desk")
        proc3, _ = Process.objects.get_or_create(department=dept2, name="Chat Support", description="Live Tech Chat Desk")

        # 5. Teams
        team1, _ = Team.objects.get_or_create(
            department=dept1, process=proc1, name="Support Alpha", defaults={"manager": manager, "team_leader": tl1}
        )
        team2, _ = Team.objects.get_or_create(
            department=dept2, process=proc3, name="Tech Beta", defaults={"manager": manager, "team_leader": tl2}
        )

        # 6. Shifts
        shift_m, _ = Shift.objects.get_or_create(name="Morning Shift", start_time="09:00:00", end_time="18:00:00", break_duration_minutes=60)
        shift_e, _ = Shift.objects.get_or_create(name="Evening Shift", start_time="14:00:00", end_time="23:00:00", break_duration_minutes=60)
        shift_n, _ = Shift.objects.get_or_create(name="Night Shift", start_time="22:00:00", end_time="07:00:00", break_duration_minutes=60, is_overnight=True)

        # 7. Break Types
        BreakType.objects.get_or_create(name="Lunch Break", duration_minutes=45, is_paid=False)
        BreakType.objects.get_or_create(name="Tea Break", duration_minutes=15, is_paid=True)
        BreakType.objects.get_or_create(name="Personal Break", duration_minutes=15, is_paid=False)

        # 8. Leave Types
        lt_c, _ = LeaveType.objects.get_or_create(name="Casual Leave", default_days=12)
        lt_s, _ = LeaveType.objects.get_or_create(name="Sick Leave", default_days=12)
        lt_e, _ = LeaveType.objects.get_or_create(name="Earned Leave", default_days=15)

        # 9. KPIs
        kpi1, _ = KPI.objects.get_or_create(name="Calls Handled", unit="Calls", target_type=KPITargetType.NUMBER, default_target=Decimal("50.00"))
        kpi2, _ = KPI.objects.get_or_create(name="Quality Score", unit="%", target_type=KPITargetType.PERCENTAGE, default_target=Decimal("95.00"))
        kpi3, _ = KPI.objects.get_or_create(name="Tickets Resolved", unit="Tickets", target_type=KPITargetType.NUMBER, default_target=Decimal("30.00"))

        # 10. Employees (10 sample employees)
        today = timezone.localdate()
        for i in range(1, 11):
            emp_username = f"emp{i}"
            emp_code = f"EMP{i:03d}"
            user, _ = User.objects.get_or_create(
                username=emp_username,
                defaults={
                    "email": f"{emp_username}@bpo.com",
                    "first_name": f"Employee_{i}",
                    "last_name": "BPO",
                    "role": Role.EMPLOYEE,
                    "employee_id": emp_code,
                },
            )
            user.set_password("EmpPassword123!")
            user.save()

            chosen_team = team1 if i <= 5 else team2
            chosen_dept = chosen_team.department
            chosen_proc = chosen_team.process
            chosen_tl = chosen_team.team_leader

            profile, _ = EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "employee_code": emp_code,
                    "date_of_joining": datetime.date(2026, 1, 1),
                    "designation": "Customer Service Representative" if i <= 5 else "Technical Support Agent",
                    "department": chosen_dept,
                    "process": chosen_proc,
                    "team": chosen_team,
                    "reporting_manager": manager,
                    "team_leader": chosen_tl,
                    "phone": f"98765432{i:02d}",
                    "status": EmployeeStatus.ACTIVE,
                },
            )

            # Assign shift
            EmployeeShift.objects.get_or_create(
                employee=profile,
                shift=shift_m if i <= 5 else shift_e,
                effective_from=datetime.date(2026, 1, 1),
                defaults={"assigned_by": manager},
            )

            # Assign Leave Balances
            for lt in [lt_c, lt_s, lt_e]:
                LeaveBalance.objects.get_or_create(
                    employee=profile,
                    leave_type=lt,
                    year=today.year,
                    defaults={
                        "allocated_days": Decimal(str(lt.default_days)),
                        "used_days": Decimal("0.0"),
                        "remaining_days": Decimal(str(lt.default_days)),
                    },
                )

            # Today Attendance
            Attendance.objects.get_or_create(
                employee=profile,
                date=today,
                defaults={
                    "status": AttendanceStatus.PRESENT,
                    "late_minutes": 5 if i % 3 == 0 else 0,
                    "remarks": "On duty",
                },
            )

            # Performance record today
            PerformanceRecord.objects.get_or_create(
                employee=profile,
                kpi=kpi1 if i <= 5 else kpi3,
                date=today,
                defaults={
                    "target_value": Decimal("50.00") if i <= 5 else Decimal("30.00"),
                    "actual_value": Decimal("48.00") if i <= 5 else Decimal("32.00"),
                    "created_by": chosen_tl,
                },
            )

            # Sample task
            Task.objects.get_or_create(
                title=f"Daily Queue Management - {emp_code}",
                assigned_to=profile,
                defaults={
                    "description": "Handle assigned customer queue tickets.",
                    "assigned_by": chosen_tl,
                    "team": chosen_team,
                    "priority": TaskPriority.HIGH if i % 2 == 0 else TaskPriority.MEDIUM,
                    "status": TaskStatus.IN_PROGRESS,
                    "due_date": today,
                },
            )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded with demo data!"))
        self.stdout.write(self.style.SUCCESS("Demo Login Credentials:"))
        self.stdout.write("  Super Admin: username='admin', password='AdminPassword123!'")
        self.stdout.write("  Manager:     username='manager1', password='ManagerPassword123!'")
        self.stdout.write("  Team Leader: username='tl1', password='TLPassword123!'")
        self.stdout.write("  Employee:    username='emp1', password='EmpPassword123!'")
