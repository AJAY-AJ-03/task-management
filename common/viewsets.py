from rest_framework import status, viewsets

from .responses import success_response


class EnvelopeModelViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet whose retrieve/create/update/destroy responses use the project's
    standard envelope. List responses are wrapped by common.pagination.StandardPagination.
    Subclasses may override *_message for per-resource wording.
    """

    retrieve_message = "Record retrieved successfully."
    create_message = "Record created successfully."
    update_message = "Record updated successfully."
    delete_message = "Record deleted successfully."

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return success_response(serializer.data, self.retrieve_message)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, self.create_message, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}
        return success_response(serializer.data, self.update_message)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(message=self.delete_message)