"""
Report Generation API Routes (Phase 6.2)

FastAPI routes for multi-view report generation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ReportViewType(str, Enum):
    """Report view types."""

    consumer = "consumer"
    operator = "operator"
    analyst = "analyst"
    audit = "audit"


class ExportFormatType(str, Enum):
    """Export format types."""

    json = "json"
    html = "html"
    markdown = "markdown"
    pdf = "pdf"


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    data: Dict[str, Any] = Field(..., description="Data to include in report")
    view: ReportViewType = Field(default=ReportViewType.consumer)
    title: Optional[str] = None
    include_sections: Optional[List[str]] = None


class ReportSection(BaseModel):
    """A report section."""

    id: str
    title: str
    content: Dict[str, Any]
    description: Optional[str] = None
    order: int


class GenerateReportResponse(BaseModel):
    """Response from report generation."""

    report_id: str
    title: str
    view: str
    generated_at: str
    sections: List[ReportSection]
    disclaimer: str
    footer: Dict[str, Any]


# Report storage (in production, use Redis or database)
_reports: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# ROUTES
# =============================================================================


@router.get("/views")
async def list_views():
    """
    List available report views.
    """
    return {
        "views": [
            {
                "id": "consumer",
                "name": "Consumer View",
                "description": "Simple, clear language",
            },
            {
                "id": "operator",
                "name": "Operator View",
                "description": "Technical details",
            },
            {
                "id": "analyst",
                "name": "Analyst View",
                "description": "Full data and metrics",
            },
            {
                "id": "audit",
                "name": "Audit View",
                "description": "Complete provenance trail",
            },
        ]
    }


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest):
    """
    Generate a report from data.

    Supports multiple views: consumer, operator, analyst, audit.
    """
    try:
        from datagod.ux import MultiViewReportGenerator, ReportView

        generator = MultiViewReportGenerator()

        # Map string to enum
        view_map = {
            "consumer": ReportView.CONSUMER,
            "operator": ReportView.OPERATOR,
            "analyst": ReportView.ANALYST,
            "audit": ReportView.AUDIT,
        }
        view = view_map.get(request.view.value, ReportView.CONSUMER)

        report = generator.generate(
            data=request.data,
            view=view,
            title=request.title,
            include_sections=request.include_sections,
        )

        # Store for later export
        _reports[report["report_id"]] = report

        # Convert sections
        sections = [
            ReportSection(
                id=s.get("id", "section"),
                title=s.get("title", "Section"),
                content=s.get("content", {}),
                description=s.get("description"),
                order=s.get("order", 0),
            )
            for s in report.get("sections", [])
        ]

        return GenerateReportResponse(
            report_id=report["report_id"],
            title=report["title"],
            view=report["view"],
            generated_at=report["generated_at"],
            sections=sections,
            disclaimer=report.get("disclaimer", ""),
            footer=report.get("footer", {}),
        )

    except Exception as e:
        logger.error(f"Generate report failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{report_id}")
async def get_report(report_id: str):
    """
    Get a previously generated report.
    """
    report = _reports.get(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    return report


@router.get("/{report_id}/export")
async def export_report(
    report_id: str, format: ExportFormatType = ExportFormatType.json
):
    """
    Export a report in the specified format.

    Supports: json, html, markdown, pdf
    """
    try:
        from datagod.ux import ExportFormat, MultiViewReportGenerator

        report = _reports.get(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found: {report_id}",
            )

        generator = MultiViewReportGenerator()

        # Map format
        format_map = {
            "json": ExportFormat.JSON,
            "html": ExportFormat.HTML,
            "markdown": ExportFormat.MARKDOWN,
            "pdf": ExportFormat.PDF,
        }
        export_format = format_map.get(format.value, ExportFormat.JSON)

        exported = generator.export(report, export_format)

        # Set appropriate content type
        content_types = {
            "json": "application/json",
            "html": "text/html",
            "markdown": "text/markdown",
            "pdf": "application/pdf",
        }
        content_type = content_types.get(format.value, "application/json")

        return Response(
            content=exported,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=report_{report_id}.{format.value}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export report failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/generate-all-views")
async def generate_all_views(request: GenerateReportRequest):
    """
    Generate report in all 4 views at once.

    Returns report IDs for each view.
    """
    try:
        from datagod.ux import MultiViewReportGenerator, ReportView

        generator = MultiViewReportGenerator()

        reports = generator.generate_all_views(data=request.data, title=request.title)

        result = {}
        for view, report in reports.items():
            _reports[report["report_id"]] = report
            result[view.value] = {
                "report_id": report["report_id"],
                "title": report["title"],
            }

        return {"reports": result}

    except Exception as e:
        logger.error(f"Generate all views failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
