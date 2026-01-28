"""
Multi-View Report Generator (Phase 4: UX Excellence)

Generates reports in multiple views for different audiences:
- Consumer View: Simple clear language
- Operator View: Technical details for researchers
- Analyst View: Data-rich with full metrics
- Audit View: Complete provenance trail for compliance
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)


class ReportView(str, Enum):
    """Available report views."""
    CONSUMER = "consumer"      # Simple, clear language
    OPERATOR = "operator"      # Technical details
    ANALYST = "analyst"        # Full data and metrics
    AUDIT = "audit"            # Complete provenance trail


class ExportFormat(str, Enum):
    """Export formats."""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"


@dataclass
class ReportSection:
    """A section in a report."""
    id: str
    title: str
    content: Dict[str, Any]
    view_specific: Dict[ReportView, Dict[str, Any]] = field(default_factory=dict)
    order: int = 0


@dataclass
class ReportMetadata:
    """Metadata for a report."""
    report_id: str
    generated_at: datetime
    generated_by: str
    version: str
    data_freshness: Dict[str, datetime]
    sources: List[Dict[str, str]]


class MultiViewReportGenerator:
    """
    Generates reports with multiple view templates.
    
    Design Philosophy:
    - Multi-Audience: Same data, different presentations
    - Compliant Phrasing: Regulatory-safe language
    - Transparent: Sources and confidence always visible
    - Exportable: Multiple format options
    """
    
    # Compliant phrasing templates
    COMPLIANT_PHRASES = {
        # Certainty qualifiers
        "confirmed": "Based on verified records,",
        "likely": "Available records indicate that",
        "possible": "Records suggest that",
        "uncertain": "There may be",
        "unknown": "Information regarding {topic} is not available in searched records",
        
        # Data freshness
        "current": "As of {date},",
        "stale": "Based on records from {date} (verification recommended),",
        "historical": "Historical records from {date} show that",
        
        # Liability disclaimers
        "lien_disclaimer": "This lien search is based on available public records and may not reflect all liens or encumbrances.",
        "not_legal_advice": "This report is for informational purposes only and does not constitute legal, financial, or professional advice.",
        "verify_independently": "Users should independently verify all information with authoritative sources before making decisions.",
    }
    
    # Section templates for each view
    VIEW_TEMPLATES = {
        ReportView.CONSUMER: {
            "style": "simple",
            "include_technical": False,
            "include_raw_data": False,
            "include_sources": "summary",
            "language_level": "plain"
        },
        ReportView.OPERATOR: {
            "style": "technical",
            "include_technical": True,
            "include_raw_data": False,
            "include_sources": "detailed",
            "language_level": "professional"
        },
        ReportView.ANALYST: {
            "style": "data_rich",
            "include_technical": True,
            "include_raw_data": True,
            "include_sources": "detailed",
            "language_level": "technical"
        },
        ReportView.AUDIT: {
            "style": "audit",
            "include_technical": True,
            "include_raw_data": True,
            "include_sources": "complete",
            "language_level": "formal",
            "include_provenance": True,
            "include_checksums": True
        }
    }
    
    def __init__(self):
        self._report_cache: Dict[str, Dict[str, Any]] = {}
    
    def generate(
        self,
        data: Dict[str, Any],
        view: ReportView = ReportView.CONSUMER,
        title: Optional[str] = None,
        include_sections: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a report from data.
        
        Args:
            data: The data to include in the report
            view: Which view template to use
            title: Report title
            include_sections: Which sections to include (None = all)
            metadata: Additional metadata to include
        
        Returns:
            Generated report as a dictionary
        """
        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        template = self.VIEW_TEMPLATES[view]
        
        # Build report structure
        report = {
            "report_id": report_id,
            "title": title or "Research Report",
            "view": view.value,
            "generated_at": datetime.utcnow().isoformat(),
            "disclaimer": self.COMPLIANT_PHRASES["not_legal_advice"],
            "sections": []
        }
        
        # Add metadata if audit view
        if view == ReportView.AUDIT:
            report["metadata"] = self._build_audit_metadata(data, metadata)
        
        # Generate sections based on data type
        if "property" in data or "property_search" in data:
            report["sections"].append(
                self._generate_property_section(data, view, template)
            )
        
        if "liens" in data or "lien_search" in data:
            report["sections"].append(
                self._generate_lien_section(data, view, template)
            )
        
        if "scenarios" in data:
            report["sections"].append(
                self._generate_scenario_section(data, view, template)
            )
        
        if "blockers" in data:
            report["sections"].append(
                self._generate_blocker_section(data, view, template)
            )
        
        if "risk_assessment" in data:
            report["sections"].append(
                self._generate_risk_section(data, view, template)
            )
        
        # Add summary section
        report["sections"].insert(0, self._generate_summary_section(data, view, template))
        
        # Filter sections if specified
        if include_sections:
            report["sections"] = [s for s in report["sections"] if s["id"] in include_sections]
        
        # Add footer
        report["footer"] = self._generate_footer(view)
        
        # Cache for export
        self._report_cache[report_id] = report
        
        return report
    
    def generate_all_views(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> Dict[ReportView, Dict[str, Any]]:
        """Generate report in all views."""
        reports = {}
        for view in ReportView:
            reports[view] = self.generate(data, view, title)
        return reports
    
    def export(
        self,
        report: Dict[str, Any],
        format: ExportFormat = ExportFormat.JSON
    ) -> Union[str, bytes]:
        """
        Export a report to the specified format.
        
        Args:
            report: The report dictionary
            format: Export format
        
        Returns:
            Exported report as string or bytes
        """
        if format == ExportFormat.JSON:
            return json.dumps(report, indent=2, default=str)
        
        elif format == ExportFormat.MARKDOWN:
            return self._export_markdown(report)
        
        elif format == ExportFormat.HTML:
            return self._export_html(report)
        
        elif format == ExportFormat.PDF:
            # Would integrate with WeasyPrint or similar
            return self._export_pdf_placeholder(report)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_summary_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary section."""
        
        # Extract key facts
        key_facts = []
        
        if data.get("property"):
            prop = data["property"]
            key_facts.append(f"Property: {prop.get('address', 'Address on file')}")
        
        if data.get("liens"):
            liens = data["liens"]
            if isinstance(liens, dict):
                lien_list = liens.get("liens", [])
            else:
                lien_list = liens
            if lien_list:
                total = sum(float(l.get("amount", 0) or 0) for l in lien_list)
                key_facts.append(f"Total Liens: ${total:,.2f} ({len(lien_list)} liens)")
        
        if data.get("risk_assessment"):
            risk = data["risk_assessment"]
            score = risk.get("risk_score", {}).get("overall", 0)
            category = risk.get("risk_score", {}).get("category", "unknown")
            key_facts.append(f"Risk Assessment: {category.title()} ({score:.0%})")
        
        summary_text = self._format_for_view(
            key_facts,
            view,
            template
        )
        
        return {
            "id": "summary",
            "title": "Executive Summary" if view != ReportView.CONSUMER else "Summary",
            "content": {
                "key_facts": key_facts,
                "text": summary_text
            },
            "order": 0
        }
    
    def _generate_property_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate property section."""
        prop_data = data.get("property") or data.get("property_search", {})
        
        content = {
            "address": prop_data.get("address"),
            "property_type": prop_data.get("property_type"),
            "owner": prop_data.get("owner_name"),
        }
        
        if template["include_technical"]:
            content.update({
                "parcel_id": prop_data.get("parcel_id"),
                "legal_description": prop_data.get("legal_description"),
                "zoning": prop_data.get("zoning"),
            })
        
        if template["include_raw_data"]:
            content["raw_data"] = prop_data
        
        # View-specific formatting
        if view == ReportView.CONSUMER:
            description = self._consumer_property_description(content)
        elif view == ReportView.OPERATOR:
            description = self._operator_property_description(content)
        else:
            description = self._analyst_property_description(content)
        
        return {
            "id": "property",
            "title": "Property Information",
            "content": content,
            "description": description,
            "order": 10
        }
    
    def _generate_lien_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate lien section."""
        lien_data = data.get("liens") or data.get("lien_search", {})
        
        if isinstance(lien_data, dict):
            liens = lien_data.get("liens", [])
        else:
            liens = lien_data
        
        # Calculate totals
        total_amount = sum(float(l.get("amount", 0) or 0) for l in liens)
        by_type = {}
        for lien in liens:
            ltype = lien.get("type", "other")
            by_type[ltype] = by_type.get(ltype, 0) + float(lien.get("amount", 0) or 0)
        
        content = {
            "total_liens": len(liens),
            "total_amount": total_amount,
            "by_type": by_type
        }
        
        if template["include_technical"]:
            content["lien_details"] = liens
        
        # Add disclaimer
        disclaimer = self.COMPLIANT_PHRASES["lien_disclaimer"]
        
        # View-specific text
        if view == ReportView.CONSUMER:
            if liens:
                description = f"We found {len(liens)} liens totaling ${total_amount:,.2f}. {disclaimer}"
            else:
                description = f"No liens were found in the searched records. {disclaimer}"
        else:
            description = f"Lien search returned {len(liens)} records with aggregate value of ${total_amount:,.2f}."
        
        return {
            "id": "liens",
            "title": "Liens & Encumbrances",
            "content": content,
            "description": description,
            "disclaimer": disclaimer,
            "order": 20
        }
    
    def _generate_scenario_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate scenario analysis section."""
        scenarios = data.get("scenarios", [])
        
        # Group by confidence
        high_conf = [s for s in scenarios if s.get("confidence_score", 0) >= 0.6]
        possible = [s for s in scenarios if 0.3 <= s.get("confidence_score", 0) < 0.6]
        
        content = {
            "total_scenarios": len(scenarios),
            "high_confidence": len(high_conf),
            "possible": len(possible)
        }
        
        if template["include_technical"]:
            content["scenario_details"] = scenarios
        
        if view == ReportView.CONSUMER:
            if high_conf:
                top = high_conf[0]
                description = f"The most likely scenario is: {top.get('scenario_name')}. We identified {len(scenarios)} possible scenarios overall."
            else:
                description = "Several possible scenarios were identified. Additional data may be needed for higher confidence."
        else:
            description = f"Scenario analysis identified {len(high_conf)} high-confidence and {len(possible)} possible scenarios."
        
        return {
            "id": "scenarios",
            "title": "Scenario Analysis",
            "content": content,
            "description": description,
            "order": 30
        }
    
    def _generate_blocker_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate blocker analysis section."""
        blockers = data.get("blockers", [])
        
        # Count by severity
        critical = [b for b in blockers if b.get("severity") == "critical"]
        high = [b for b in blockers if b.get("severity") == "high"]
        
        content = {
            "total_blockers": len(blockers),
            "critical_count": len(critical),
            "high_count": len(high)
        }
        
        if template["include_technical"]:
            content["blocker_details"] = blockers
        
        if view == ReportView.CONSUMER:
            if critical:
                description = f"⚠️ There are {len(critical)} critical issues that must be resolved. "
            elif high:
                description = f"There are {len(high)} important issues to address. "
            else:
                description = "No major blockers were identified. "
            
            if blockers:
                description += "See the fix list below for recommended actions."
        else:
            description = f"Identified {len(blockers)} blockers: {len(critical)} critical, {len(high)} high priority."
        
        return {
            "id": "blockers",
            "title": "Blockers & Fix List",
            "content": content,
            "description": description,
            "order": 40
        }
    
    def _generate_risk_section(
        self,
        data: Dict[str, Any],
        view: ReportView,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate risk assessment section."""
        risk = data.get("risk_assessment", {})
        
        risk_score = risk.get("risk_score", {})
        red_flags = risk.get("red_flags", [])
        recommendations = risk.get("recommendations", [])
        
        content = {
            "overall_score": risk_score.get("overall", 0),
            "category": risk_score.get("category", "unknown"),
            "red_flags_count": len(red_flags)
        }
        
        if template["include_technical"]:
            content["red_flag_details"] = red_flags
            content["recommendations"] = recommendations
        
        category = risk_score.get("category", "unknown")
        score = risk_score.get("overall", 0)
        
        if view == ReportView.CONSUMER:
            risk_descriptions = {
                "low": "This property has a low risk profile based on available records.",
                "medium": "This property has moderate risk factors that should be reviewed.",
                "high": "This property has significant risk factors requiring careful consideration.",
                "critical": "⚠️ This property has critical risk factors. Professional review recommended."
            }
            description = risk_descriptions.get(category, "Risk level could not be determined.")
        else:
            description = f"Risk score: {score:.0%} ({category}). {len(red_flags)} red flags identified."
        
        return {
            "id": "risk",
            "title": "Risk Assessment",
            "content": content,
            "description": description,
            "order": 50
        }
    
    def _generate_footer(self, view: ReportView) -> Dict[str, Any]:
        """Generate report footer with disclaimers."""
        footer = {
            "disclaimer": self.COMPLIANT_PHRASES["not_legal_advice"],
            "verify_note": self.COMPLIANT_PHRASES["verify_independently"],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        if view == ReportView.AUDIT:
            footer["audit_note"] = "This report includes complete provenance and is suitable for audit purposes."
        
        return footer
    
    def _build_audit_metadata(
        self,
        data: Dict[str, Any],
        extra_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete audit metadata."""
        import hashlib
        
        metadata = {
            "report_version": "1.0.0",
            "generator_version": "DataGod 2.0",
            "generated_at": datetime.utcnow().isoformat(),
            "data_hash": hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16],
            "sources": [],
            "data_freshness": {}
        }
        
        # Extract sources from data
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and value.get("source"):
                    metadata["sources"].append({
                        "data_type": key,
                        "source": value.get("source"),
                        "timestamp": value.get("timestamp", "unknown")
                    })
        
        if extra_metadata:
            metadata.update(extra_metadata)
        
        return metadata
    
    def _format_for_view(
        self,
        items: List[str],
        view: ReportView,
        template: Dict[str, Any]
    ) -> str:
        """Format items for the specified view."""
        if view == ReportView.CONSUMER:
            return ". ".join(items) + "." if items else "No information available."
        elif view == ReportView.OPERATOR:
            return "\n".join([f"• {item}" for item in items])
        else:
            return "\n".join([f"- {item}" for item in items])
    
    def _consumer_property_description(self, content: Dict[str, Any]) -> str:
        """Generate consumer-friendly property description."""
        parts = []
        if content.get("address"):
            parts.append(f"The property at {content['address']}")
        if content.get("property_type"):
            parts.append(f"is a {content['property_type'].replace('_', ' ')}")
        if content.get("owner"):
            parts.append(f"currently owned by {content['owner']}")
        return " ".join(parts) + "." if parts else "Property information on file."
    
    def _operator_property_description(self, content: Dict[str, Any]) -> str:
        """Generate operator-level property description."""
        lines = []
        for key, value in content.items():
            if value and key != "raw_data":
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines)
    
    def _analyst_property_description(self, content: Dict[str, Any]) -> str:
        """Generate analyst-level property description."""
        return json.dumps(content, indent=2, default=str)
    
    def _export_markdown(self, report: Dict[str, Any]) -> str:
        """Export report to Markdown."""
        lines = [
            f"# {report.get('title', 'Report')}",
            "",
            f"*Generated: {report.get('generated_at')}*",
            f"*View: {report.get('view', 'unknown').title()}*",
            "",
            f"> {report.get('disclaimer', '')}",
            "",
        ]
        
        for section in report.get("sections", []):
            lines.append(f"## {section.get('title', 'Section')}")
            lines.append("")
            
            if section.get("description"):
                lines.append(section["description"])
                lines.append("")
            
            content = section.get("content", {})
            for key, value in content.items():
                if not isinstance(value, (dict, list)):
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            
            lines.append("")
        
        footer = report.get("footer", {})
        if footer:
            lines.append("---")
            lines.append(f"*{footer.get('disclaimer', '')}*")
            lines.append(f"*{footer.get('verify_note', '')}*")
        
        return "\n".join(lines)
    
    def _export_html(self, report: Dict[str, Any]) -> str:
        """Export report to HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report.get('title', 'Report')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; }}
        h2 {{ color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 5px; }}
        .disclaimer {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
        .section {{ margin: 20px 0; }}
        .content {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>{report.get('title', 'Report')}</h1>
    <p><em>Generated: {report.get('generated_at')}</em></p>
    <div class="disclaimer">{report.get('disclaimer', '')}</div>
"""
        
        for section in report.get("sections", []):
            html += f"""
    <div class="section">
        <h2>{section.get('title', 'Section')}</h2>
        <p>{section.get('description', '')}</p>
        <div class="content">
"""
            content = section.get("content", {})
            for key, value in content.items():
                if not isinstance(value, (dict, list)):
                    html += f"<p><strong>{key.replace('_', ' ').title()}</strong>: {value}</p>"
            html += "</div></div>"
        
        footer = report.get("footer", {})
        html += f"""
    <div class="footer">
        <p>{footer.get('disclaimer', '')}</p>
        <p>{footer.get('verify_note', '')}</p>
    </div>
</body>
</html>"""
        
        return html
    
    def _export_pdf_placeholder(self, report: Dict[str, Any]) -> str:
        """Placeholder for PDF export (would use WeasyPrint)."""
        # In production, would use WeasyPrint or similar
        html = self._export_html(report)
        return f"<!-- PDF Export Placeholder -->\n{html}"
