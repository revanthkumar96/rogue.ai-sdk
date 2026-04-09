"""Dashboard API routes for SDK documentation and introspection.

This module provides REST endpoints for the dashboard frontend to query
SDK capabilities, configuration, and user's traced functions.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from rouge_ai.introspection import (get_all_decorators, get_all_functions,
                                    get_config_schema, get_examples,
                                    get_traced_functions)
from rouge_ai.schema import (export_schema_as_json, export_schema_as_markdown,
                             generate_config_schema_formatted,
                             generate_decorator_schema,
                             generate_function_schema,
                             generate_quick_reference, generate_sdk_schema)


def create_api_router() -> APIRouter:
    """Create and configure the API router for SDK documentation endpoints.

    Returns:
        Configured APIRouter instance
    """
    router = APIRouter(prefix="/api", tags=["sdk-docs"])

    @router.get("/sdk/schema")
    async def get_sdk_schema():
        """Get complete SDK schema including functions, decorators, and config.

        Returns:
            Full SDK schema as JSON
        """
        try:
            schema = generate_sdk_schema()
            return JSONResponse(content=schema)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to generate schema: {str(e)}")

    @router.get("/sdk/schema/json")
    async def get_sdk_schema_json():
        """Get the SDK schema as a formatted JSON string.

        Returns:
            JSON string representation of the schema
        """
        try:
            json_str = export_schema_as_json()
            return JSONResponse(content={"schema": json_str})
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to export schema: {str(e)}")

    @router.get("/sdk/schema/markdown")
    async def get_sdk_schema_markdown():
        """Get the SDK schema as Markdown documentation.

        Returns:
            Markdown string representation of the schema
        """
        try:
            markdown = export_schema_as_markdown()
            return JSONResponse(content={"markdown": markdown})
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to export markdown: {str(e)}")

    @router.get("/sdk/decorators")
    async def get_decorators():
        """Get all available decorators.

        Returns:
            Dictionary of decorator names to metadata
        """
        try:
            decorators = get_all_decorators()
            return JSONResponse(content=decorators)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get decorators: {str(e)}")

    @router.get("/sdk/decorators/{decorator_name}")
    async def get_decorator(decorator_name: str):
        """Get details for a specific decorator.

        Args:
            decorator_name: Name of the decorator

        Returns:
            Decorator metadata
        """
        try:
            decorator = generate_decorator_schema(decorator_name)
            if not decorator:
                raise HTTPException(
                    status_code=404,
                    detail=f"Decorator '{decorator_name}' not found")
            return JSONResponse(content=decorator)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get decorator: {str(e)}")

    @router.get("/sdk/functions")
    async def get_functions():
        """Get all available SDK functions.

        Returns:
            Dictionary of function names to metadata
        """
        try:
            functions = get_all_functions()
            return JSONResponse(content=functions)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get functions: {str(e)}")

    @router.get("/sdk/functions/{function_name:path}")
    async def get_function(function_name: str):
        """Get details for a specific function.

        Args:
            function_name: Fully qualified function name
                (e.g., "rouge_ai.init")

        Returns:
            Function metadata
        """
        try:
            function = generate_function_schema(function_name)
            if not function:
                raise HTTPException(
                    status_code=404,
                    detail=f"Function '{function_name}' not found")
            return JSONResponse(content=function)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get function: {str(e)}")

    @router.get("/sdk/config")
    async def get_config():
        """Get the configuration schema with all available options.

        Returns:
            Configuration schema organized by category
        """
        try:
            config = get_config_schema()
            return JSONResponse(content=config)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get config schema: {str(e)}")

    @router.get("/sdk/config/formatted")
    async def get_config_formatted():
        """Get the formatted configuration schema with examples.

        Returns:
            Configuration schema with usage examples
        """
        try:
            config = generate_config_schema_formatted()
            return JSONResponse(content=config)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get formatted config: {str(e)}")

    @router.get("/sdk/examples")
    async def get_sdk_examples():
        """Get usage examples organized by category.

        Returns:
            Dictionary of categories to code examples
        """
        try:
            examples = get_examples()
            return JSONResponse(content=examples)
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Failed to get examples: {str(e)}")

    @router.get("/sdk/quick-reference")
    async def get_quick_reference():
        """Get a quick reference guide for the SDK.

        Returns:
            Quick reference with installation, quickstart, and common patterns
        """
        try:
            reference = generate_quick_reference()
            return JSONResponse(content=reference)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get quick reference: {str(e)}")

    @router.get("/traced/functions")
    async def get_user_traced_functions():
        """Get all user's @trace decorated functions.

        This returns functions that the user has decorated with @trace()
        in their application code.

        Returns:
            Dictionary of function names to metadata
        """
        try:
            traced = get_traced_functions()
            return JSONResponse(content=traced)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get traced functions: {str(e)}")

    @router.get("/health")
    async def health_check():
        """Health check endpoint for the API.

        Returns:
            Health status
        """
        return JSONResponse(content={"status": "healthy", "api": "sdk-docs"})

    return router
