
import grpc
import httpx

from proto import projects_pb2 as pb
from proto import projects_pb2_grpc as pb_grpc

from .mapper import (
    create_to_json,
    membership_to_json,
    search_to_json,
    project_to_proto,
    summary_to_proto,
)


HTTP_TO_GRPC = {
    400: grpc.StatusCode.INVALID_ARGUMENT,
    401: grpc.StatusCode.UNAUTHENTICATED,
    403: grpc.StatusCode.PERMISSION_DENIED,
    404: grpc.StatusCode.NOT_FOUND,
    409: grpc.StatusCode.FAILED_PRECONDITION,
    422: grpc.StatusCode.INVALID_ARGUMENT,
    429: grpc.StatusCode.RESOURCE_EXHAUSTED,
    500: grpc.StatusCode.INTERNAL,
    502: grpc.StatusCode.UNAVAILABLE,
    503: grpc.StatusCode.UNAVAILABLE,
    504: grpc.StatusCode.DEADLINE_EXCEEDED,
}


class ProjectsService(pb_grpc.ProjectsServiceServicer):
    def __init__(self, client):
        self.client = client

    async def _execute(self, context, operation):
        try:
            return await operation()
        except httpx.HTTPStatusError as exc:
            code = HTTP_TO_GRPC.get(
                exc.response.status_code,
                grpc.StatusCode.UNKNOWN,
            )
            await context.abort(
                code,
                f"Projects API returned HTTP {exc.response.status_code}",
            )
        except httpx.TimeoutException:
            await context.abort(
                grpc.StatusCode.DEADLINE_EXCEEDED,
                "Projects API request timed out",
            )
        except httpx.RequestError:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Projects API is unavailable",
            )
        except KeyError:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                "Project not found",
            )
        except ValueError as exc:
            message = str(exc)
            code = (
                grpc.StatusCode.ALREADY_EXISTS
                if "already" in message.lower()
                else grpc.StatusCode.FAILED_PRECONDITION
            )
            await context.abort(code, message)
        except (TypeError, OverflowError):
            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Invalid response from Projects API",
            )

    async def CreateProject(self, request, context):
        if (
            not request.creator_id.strip()
            or not request.project_id.strip()
            or not request.project_name.strip()
            or not request.org_id.strip()
            or request.budget < 0
            or any(
                not item.hardware_id.strip()
                or item.capacity <= 0
                for item in request.hardware_list
            )
        ):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid project fields",
            )
        return await self._execute(context, operation)

    async def JoinProject(self, request, context):
        return await self._membership(
            request, context, self.client.join_project
        )

    async def LeaveProject(self, request, context):
        return await self._membership(
            request, context, self.client.leave_project
        )

    async def _membership(self, request, context, action):
        if not all([
            request.org_id.strip(),
            request.project_creator_id.strip(),
            request.user_id.strip(),
        ]):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Project and user IDs are required",
            )

        async def operation():
            result = await action(membership_to_json(request))
            return pb.OperationResponse(
                success=result["success"],
                error_message=result.get("errorMessage", ""),
            )

        return await self._execute(context, operation)

    async def SearchProjects(self, request, context):
        async def operation():
            result = await self.client.search_projects(
                search_to_json(request)
            )
            return pb.SearchProjectsResponse(
                project_list=[
                    summary_to_proto(item)
                    for item in result["projectList"]
                ]
            )

        return await self._execute(context, operation)

        async def GetProject(self, request, context):
            if not request.project_id.strip():
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Project ID is required",
                )
            if not request.project_id.strip() or not request.org_id.strip():
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "Project ID and Organization ID are required",
                )

            async def operation():
                result = await self.client.get_project(
                    request.project_id,
                    request.org_id,
                )
                return pb.GetProjectResponse(
                    project_info=project_to_proto(result["projectInfo"])
                )

            return await self._execute(context, operation)
