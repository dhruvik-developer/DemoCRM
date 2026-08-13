from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import (
    Task, TaskStatus, TaskCategory, TaskPriority,
    MeetingType, Meeting, MeetingStatus, MeetingParticipant,
    Reminder, ReminderStatus, ReminderType
)
from .serializers import (
    TaskCategorySerializer, TaskPrioritySerializer, TaskSerializer, TaskStatusSerializer,
    MeetingTypeSerializer, MeetingSerializer, MeetingStatusSerializer, MeetingParticipantSerializer,
    ReminderSerializer, ReminderStatusSerializer, ReminderTypeSerializer
)
from django.utils import timezone

from FollowUp.notification_utils import create_notification, send_reminder_email


# ============================================================
# MEETING REMINDER / NOTIFICATION HELPERS
# ============================================================

def _schedule_meeting_reminder(meeting):
    """
    Called right after a Meeting is created.
    - Creates a Reminder row (visible via GET /api/tasks/reminders/).
    - Emails both the meeting organizer (created_by) and the Lead
      linked to the meeting's task (if any), reminding them of the
      upcoming meeting.
    """
    reminder_type, _ = ReminderType.objects.get_or_create(type_name="Meeting Reminder")
    reminder_status, _ = ReminderStatus.objects.get_or_create(status_name="Pending")

    reminder_dt = datetime.combine(meeting.meeting_date, meeting.start_time)
    if timezone.is_naive(reminder_dt):
        reminder_dt = timezone.make_aware(reminder_dt)

    message = (
        f"Reminder: Meeting '{meeting.meeting_title}' is scheduled on "
        f"{meeting.meeting_date} at {meeting.start_time}."
    )

    Reminder.objects.create(
        meeting_id=meeting,
        reminder_type_id=reminder_type,
        reminder_status_id=reminder_status,
        reminder_datetime=reminder_dt,
        message=message,
        created_by=meeting.created_by,
    )

    recipients = []

    if meeting.created_by and meeting.created_by.email:
        recipients.append(meeting.created_by.email)

    lead = getattr(meeting.task_id, "lead", None)
    if lead is not None and lead.email:
        recipients.append(lead.email)

    send_reminder_email(
        subject=f"Meeting Reminder: {meeting.meeting_title}",
        message=message,
        recipient_list=recipients,
    )


def _notify_meeting_completed(meeting):
    """
    Called when a Meeting's status transitions into "Completed".
    Creates an in-system Notification for the meeting organizer and,
    if different, the CustomUser assigned to the linked Lead.
    """
    message = f"Meeting '{meeting.meeting_title}' has been completed successfully."

    create_notification(
        user=meeting.created_by,
        title="Meeting Completed",
        message=message,
        type_name="Meeting",
    )

    lead = getattr(meeting.task_id, "lead", None)
    if lead is not None and lead.assigned_to_id and lead.assigned_to_id != meeting.created_by_id:
        create_notification(
            user=lead.assigned_to,
            title="Meeting Completed",
            message=message,
            type_name="Meeting",
        )


def _meeting_status_name(meeting):
    return meeting.meeting_status_id.status_name.strip().lower() if meeting.meeting_status_id else ""

#===================================== TASK
@api_view(["GET","POST"])
@permission_classes([IsAuthenticated])
def task_list_create(request):
    if request.method == "POST":
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save() 
            return Response(
                {
                    "status": "success",
                    "message": "Task created successfully.",
                    "data": TaskSerializer(task).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Task creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    tasks = Task.objects.all().order_by("-created_at")
    serializer = TaskSerializer(tasks, many=True)
    return Response(
        {
            "status": "success",
            "message": "Tasks retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def task_detail(request, task_id):

    try:
        task = Task.objects.get(task_id=task_id)

    except Task.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Task not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "GET":

        serializer = TaskSerializer(task)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    elif request.method == "PUT":

        serializer = TaskSerializer(
            task,
            data=request.data,
        )

        if serializer.is_valid():
            task = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Task updated successfully.",
                    "data": TaskSerializer(task).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "error",
                "message": "Task update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    elif request.method == "PATCH":
        serializer = TaskSerializer(
            task,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            task = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Task partially updated successfully.",
                    "data": TaskSerializer(task).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "error",
                "message": "Task update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    elif request.method == "DELETE":
        task.delete()
        return Response(
            {
                "status": "success",
                "message": "Task deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )

#=================== task status
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_status_list_create(request):
    if request.method == "POST":
        serializer = TaskStatusSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Task status created successfully.",
                    "data": TaskStatusSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    objects = TaskStatus.objects.all()
    serializer = TaskStatusSerializer(objects, many=True)
    return Response(
        {
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )
#=========================== task priority]
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_priority_list_create(request):
    if request.method == "POST":
        serializer = TaskPrioritySerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Task priority created successfully.",
                    "data": TaskPrioritySerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    objects = TaskPriority.objects.all()
    serializer = TaskPrioritySerializer(objects, many=True)
    return Response(
        {
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )
#=============================== task category 
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def task_category_list_create(request):
    if request.method == "POST":
        serializer = TaskCategorySerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Task category created successfully.",
                    "data": TaskCategorySerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    objects = TaskCategory.objects.all()
    serializer = TaskCategorySerializer(objects, many=True)
    return Response(
        {
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


#=============================================== meeting
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def meeting_list_create(request):

    if request.method == "POST":
        serializer = MeetingSerializer(data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            _schedule_meeting_reminder(obj)
            return Response(
                {
                    "status": "success",
                    "message": "Meeting created successfully. A reminder has been scheduled and emailed to the organizer and the lead.",
                    "data": MeetingSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": "error",
                "message": "Meeting creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    objects = Meeting.objects.all().order_by("-created_at")
    serializer = MeetingSerializer(objects, many=True)
    return Response(
        {
            "status": "success",
            "data": serializer.data,
        }
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def meeting_detail(request, meeting_id):
    try:
        obj = Meeting.objects.get(meeting_id=meeting_id)
    except Meeting.DoesNotExist:
        return Response(
            {
                "status": "error",
                "message": "Meeting not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "GET":
        serializer = MeetingSerializer(obj)
        return Response(
            {
                "status": "success",
                "data": serializer.data,
            }
        )

    was_completed = _meeting_status_name(obj) == "completed"

    if request.method == "PUT":
        serializer = MeetingSerializer(
            obj,
            data=request.data,
        )
        if serializer.is_valid():
            obj = serializer.save()
            if not was_completed and _meeting_status_name(obj) == "completed":
                _notify_meeting_completed(obj)
            return Response(
                {
                    "status": "success",
                    "message": "Meeting updated successfully.",
                    "data": MeetingSerializer(obj).data,
                }
            )
        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    elif request.method == "PATCH":
        serializer = MeetingSerializer(
            obj,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            obj = serializer.save()
            if not was_completed and _meeting_status_name(obj) == "completed":
                _notify_meeting_completed(obj)
            return Response(
                {
                    "status": "success",
                    "message": "Meeting partially updated successfully.",
                    "data": MeetingSerializer(obj).data,
                }
            )
        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    elif request.method == "DELETE":
        obj.delete()
        return Response(
            {
                "status": "success",
                "message": "Meeting deleted successfully.",
            }
        )
#===========================meeting participant
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def meeting_participant_list_create(request):

    if request.method == "POST":

        serializer = MeetingParticipantSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting participant added successfully.",
                    "data": MeetingParticipantSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objects = MeetingParticipant.objects.all()

    serializer = MeetingParticipantSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "data": serializer.data,
        }
    )
#======================meeting status
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def meeting_status_list_create(request):
    if request.method == "POST":

        serializer = MeetingStatusSerializer(data=request.data)

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting status created successfully.",
                    "data": MeetingStatusSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting status creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    objects = MeetingStatus.objects.all()

    serializer = MeetingStatusSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Meeting statuses retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def meeting_status_detail(request, meeting_status_id):

    try:
        obj = MeetingStatus.objects.get(
            meeting_status_id=meeting_status_id
        )

    except MeetingStatus.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Meeting status not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "GET":

        serializer = MeetingStatusSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    elif request.method == "PUT":

        serializer = MeetingStatusSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting status updated successfully.",
                    "data": MeetingStatusSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting status update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    elif request.method == "PATCH":

        serializer = MeetingStatusSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting status partially updated successfully.",
                    "data": MeetingStatusSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting status update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Meeting status deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )

#meeting_type
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def meeting_type_list_create(request):

    if request.method == "POST":

        serializer = MeetingTypeSerializer(data=request.data)

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting type created successfully.",
                    "data": MeetingTypeSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting type creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )



    objects = MeetingType.objects.all()

    serializer = MeetingTypeSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Meeting types retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def meeting_type_detail(request, meeting_type_id):

    try:
        obj = MeetingType.objects.get(
            meeting_type_id=meeting_type_id
        )

    except MeetingType.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Meeting type not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":

        serializer = MeetingTypeSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "PUT":

        serializer = MeetingTypeSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting type updated successfully.",
                    "data": MeetingTypeSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting type update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


    elif request.method == "PATCH":

        serializer = MeetingTypeSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Meeting type partially updated successfully.",
                    "data": MeetingTypeSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Meeting type update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Meeting type deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )

#========================= reminde6r
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def reminder_list_create(request):

    if request.method == "POST":

        serializer = ReminderSerializer(data=request.data)

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder created successfully.",
                    "data": ReminderSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objects = Reminder.objects.all().order_by("-created_at")

    serializer = ReminderSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "data": serializer.data,
        }
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reminder_detail(request, reminder_id):

    try:
        obj = Reminder.objects.get(reminder_id=reminder_id)

    except Reminder.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Reminder not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":

        serializer = ReminderSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            }
        )

    elif request.method == "PUT":

        serializer = ReminderSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder updated successfully.",
                    "data": ReminderSerializer(obj).data,
                }
            )

        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "PATCH":

        serializer = ReminderSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder partially updated successfully.",
                    "data": ReminderSerializer(obj).data,
                }
            )

        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Reminder deleted successfully.",
            }
        )
#========================= reminder status 
# ============================================================
# REMINDER TYPE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def reminder_type_list_create(request):


    if request.method == "POST":

        serializer = ReminderTypeSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder type created successfully.",
                    "data": ReminderTypeSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder type creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objects = ReminderType.objects.all()

    serializer = ReminderTypeSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Reminder types retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reminder_type_detail(request, reminder_type_id):

    try:
        obj = ReminderType.objects.get(
            reminder_type_id=reminder_type_id
        )

    except ReminderType.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Reminder type not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


    if request.method == "GET":

        serializer = ReminderTypeSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "PUT":

        serializer = ReminderTypeSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder type updated successfully.",
                    "data": ReminderTypeSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder type update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


    elif request.method == "PATCH":

        serializer = ReminderTypeSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder type partially updated successfully.",
                    "data": ReminderTypeSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder type update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Reminder type deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# REMINDER STATUS
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def reminder_status_list_create(request):


    if request.method == "POST":

        serializer = ReminderStatusSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder status created successfully.",
                    "data": ReminderStatusSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder status creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objects = ReminderStatus.objects.all()

    serializer = ReminderStatusSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Reminder statuses retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reminder_status_detail(request, reminder_status_id):

    try:
        obj = ReminderStatus.objects.get(
            reminder_status_id=reminder_status_id
        )

    except ReminderStatus.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Reminder status not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


    if request.method == "GET":

        serializer = ReminderStatusSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    elif request.method == "PUT":

        serializer = ReminderStatusSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder status updated successfully.",
                    "data": ReminderStatusSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder status update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "PATCH":

        serializer = ReminderStatusSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Reminder status partially updated successfully.",
                    "data": ReminderStatusSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Reminder status update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Reminder status deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )

# ============================================================
# ASSIGN TASK
# ============================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def assign_task(request, task_id):
    task = get_object_or_404(Task, task_id=task_id)

    assigned_to_id = request.data.get("assigned_to")
    if not assigned_to_id:
        return Response(
            {"status": "error", "message": "assigned_to (user_id) is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from accounts.models import CustomUser
    user = get_object_or_404(CustomUser, user_id=assigned_to_id)

    task.assigned_to = user
    task.save(update_fields=["assigned_to"])

    return Response(
        {
            "status": "success",
            "message": "Task assigned successfully.",
            "data": TaskSerializer(task).data,
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# TASK STATUS UPDATE
# ============================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def task_status_update(request, task_id):
    task = get_object_or_404(Task, task_id=task_id)

    status_id = request.data.get("status")
    if not status_id:
        return Response(
            {"status": "error", "message": "status (status_id) is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    task_status_obj = get_object_or_404(TaskStatus, status_id=status_id)

    task.status = task_status_obj
    task.save(update_fields=["status"])

    return Response(
        {
            "status": "success",
            "message": "Task status updated successfully.",
            "data": TaskSerializer(task).data,
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# DASHBOARD REPORT
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_report(request):
    from FollowUp.models import Notification

    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status__status_name__iexact="completed").count()
    pending_tasks = total_tasks - completed_tasks

    upcoming_meetings = Meeting.objects.filter(
        meeting_date__gte=timezone.now().date()
    ).count()

    pending_reminders = Reminder.objects.filter(
        reminder_status_id__status_name__iexact="pending"
    ).count()

    unread_notifications = Notification.objects.filter(
        user_id=request.user, is_read=False
    ).count()

    return Response(
        {
            "status": "success",
            "message": "Dashboard report retrieved successfully.",
            "data": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks,
                "upcoming_meetings": upcoming_meetings,
                "pending_reminders": pending_reminders,
                "unread_notifications": unread_notifications,
            },
        },
        status=status.HTTP_200_OK,
    )