from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.utils import timezone

from .models import (
    Followup,
    FollowUpStatus,
    FollowUpTypes,
    FollowUpNote,

    ActivityType,
    ActivityAction,
    ActivityLog,

    NotificationType,
    NotificationTemplate,
    Notification,
)

from .serializers import (
    FollowupSerializer,
    FollowUpStatusSerializer,
    FollowUpTypesSerializer,
    FollowUpNoteSerializer,

    ActivityTypeSerializer,
    ActivityActionSerializer,
    ActivityLogSerializer,

    NotificationTypeSerializer,
    NotificationTemplateSerializer,
    NotificationSerializer,
)


# ============================================================
# FOLLOW-UP
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def followup_list_create(request):

    # --------------------------------------------------------
    # POST - CREATE FOLLOW-UP
    # --------------------------------------------------------

    if request.method == "POST":

        serializer = FollowupSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up created successfully.",
                    "data": FollowupSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Follow-up creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # GET - LIST FOLLOW-UPS
    # --------------------------------------------------------

    objects = Followup.objects.all().order_by("-created_at")

    serializer = FollowupSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Follow-ups retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def followup_detail(request, followup_id):

    try:
        obj = Followup.objects.get(
            followup_id=followup_id
        )

    except Followup.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Follow-up not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        serializer = FollowupSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # PUT
    # --------------------------------------------------------

    elif request.method == "PUT":

        serializer = FollowupSerializer(
            obj,
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up updated successfully.",
                    "data": FollowupSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "message": "Follow-up update failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # PATCH
    # --------------------------------------------------------

    elif request.method == "PATCH":

        serializer = FollowupSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up partially updated successfully.",
                    "data": FollowupSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Follow-up deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# FOLLOW-UP STATUS
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def followup_status_list_create(request):

    if request.method == "POST":

        serializer = FollowUpStatusSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up status created successfully.",
                    "data": FollowUpStatusSerializer(obj).data,
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

    objects = FollowUpStatus.objects.all()

    serializer = FollowUpStatusSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def followup_status_detail(request, followup_status_id):

    try:
        obj = FollowUpStatus.objects.get(
            followup_status_id=followup_status_id
        )

    except FollowUpStatus.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Follow-up status not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":

        return Response(
            {
                "status": "success",
                "data": FollowUpStatusSerializer(obj).data,
            }
        )

    elif request.method in ["PUT", "PATCH"]:

        serializer = FollowUpStatusSerializer(
            obj,
            data=request.data,
            partial=(request.method == "PATCH")
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up status updated successfully.",
                    "data": FollowUpStatusSerializer(obj).data,
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
                "message": "Follow-up status deleted successfully.",
            }
        )


# ============================================================
# FOLLOW-UP TYPE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def followup_type_list_create(request):

    if request.method == "POST":

        serializer = FollowUpTypesSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up type created successfully.",
                    "data": FollowUpTypesSerializer(obj).data,
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

    objects = FollowUpTypes.objects.all()

    serializer = FollowUpTypesSerializer(
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
def followup_type_detail(request, followup_type_id):

    try:
        obj = FollowUpTypes.objects.get(
            followup_type_id=followup_type_id
        )

    except FollowUpTypes.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Follow-up type not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":

        return Response(
            {
                "status": "success",
                "data": FollowUpTypesSerializer(obj).data,
            }
        )

    elif request.method in ["PUT", "PATCH"]:

        serializer = FollowUpTypesSerializer(
            obj,
            data=request.data,
            partial=(request.method == "PATCH")
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up type updated successfully.",
                    "data": FollowUpTypesSerializer(obj).data,
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
                "message": "Follow-up type deleted successfully.",
            }
        )


# ============================================================
# FOLLOW-UP NOTE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def followup_note_list_create(request):

    if request.method == "POST":

        serializer = FollowUpNoteSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up note created successfully.",
                    "data": FollowUpNoteSerializer(obj).data,
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

    objects = FollowUpNote.objects.all().order_by("-created_at")

    serializer = FollowUpNoteSerializer(
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
def followup_note_detail(request, note_id):

    try:
        obj = FollowUpNote.objects.get(
            note_id=note_id
        )

    except FollowUpNote.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Follow-up note not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":

        return Response(
            {
                "status": "success",
                "data": FollowUpNoteSerializer(obj).data,
            }
        )

    elif request.method in ["PUT", "PATCH"]:

        serializer = FollowUpNoteSerializer(
            obj,
            data=request.data,
            partial=(request.method == "PATCH")
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Follow-up note updated successfully.",
                    "data": FollowUpNoteSerializer(obj).data,
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
                "message": "Follow-up note deleted successfully.",
            }
        )


# ============================================================
# ACTIVITY TYPE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def activity_type_list_create(request):

    if request.method == "POST":

        serializer = ActivityTypeSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Activity type created successfully.",
                    "data": ActivityTypeSerializer(obj).data,
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

    objects = ActivityType.objects.all()

    return Response(
        {
            "status": "success",
            "data": ActivityTypeSerializer(
                objects,
                many=True
            ).data,
        }
    )


# ============================================================
# ACTIVITY ACTION
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def activity_action_list_create(request):

    if request.method == "POST":

        serializer = ActivityActionSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Activity action created successfully.",
                    "data": ActivityActionSerializer(obj).data,
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

    objects = ActivityAction.objects.all()

    return Response(
        {
            "status": "success",
            "data": ActivityActionSerializer(
                objects,
                many=True
            ).data,
        }
    )


# ============================================================
# ACTIVITY LOG
# ============================================================
# Activity logs are history records.
# Therefore we only allow GET.

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def activity_log_list(request):

    objects = ActivityLog.objects.all().order_by(
        "-created_at"
    )

    serializer = ActivityLogSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Activity logs retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def activity_log_detail(request, activity_id):

    try:
        obj = ActivityLog.objects.get(
            activity_id=activity_id
        )

    except ActivityLog.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Activity log not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ActivityLogSerializer(obj)

    return Response(
        {
            "status": "success",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


# ============================================================
# NOTIFICATION TYPE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notification_type_list_create(request):

    if request.method == "POST":

        serializer = NotificationTypeSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Notification type created successfully.",
                    "data": NotificationTypeSerializer(obj).data,
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

    objects = NotificationType.objects.all()

    return Response(
        {
            "status": "success",
            "data": NotificationTypeSerializer(
                objects,
                many=True
            ).data,
        }
    )


# ============================================================
# NOTIFICATION TEMPLATE
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notification_template_list_create(request):

    if request.method == "POST":

        serializer = NotificationTemplateSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Notification template created successfully.",
                    "data": NotificationTemplateSerializer(obj).data,
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

    objects = NotificationTemplate.objects.all()

    return Response(
        {
            "status": "success",
            "data": NotificationTemplateSerializer(
                objects,
                many=True
            ).data,
        }
    )


# ============================================================
# NOTIFICATION
# ============================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def notification_list_create(request):

    if request.method == "POST":

        serializer = NotificationSerializer(
            data=request.data
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Notification created successfully.",
                    "data": NotificationSerializer(obj).data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": "error",
                "message": "Notification creation failed.",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    objects = Notification.objects.all().order_by(
        "-created_at"
    )

    serializer = NotificationSerializer(
        objects,
        many=True
    )

    return Response(
        {
            "status": "success",
            "message": "Notifications retrieved successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):

    try:
        obj = Notification.objects.get(
            notification_id=notification_id
        )

    except Notification.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Notification not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        serializer = NotificationSerializer(obj)

        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # PATCH
    # --------------------------------------------------------

    elif request.method == "PATCH":

        serializer = NotificationSerializer(
            obj,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            obj = serializer.save()

            return Response(
                {
                    "status": "success",
                    "message": "Notification updated successfully.",
                    "data": NotificationSerializer(obj).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "error",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    elif request.method == "DELETE":

        obj.delete()

        return Response(
            {
                "status": "success",
                "message": "Notification deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, notification_id):

    try:
        obj = Notification.objects.get(
            notification_id=notification_id
        )

    except Notification.DoesNotExist:

        return Response(
            {
                "status": "error",
                "message": "Notification not found.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    obj.is_read = True
    obj.read_at = timezone.now()

    obj.save(
        update_fields=[
            "is_read",
            "read_at"
        ]
    )

    return Response(
        {
            "status": "success",
            "message": "Notification marked as read.",
            "data": NotificationSerializer(obj).data,
        },
        status=status.HTTP_200_OK,
    )