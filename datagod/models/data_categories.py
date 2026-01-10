"""
Extended Data Category Models

Provides SQLAlchemy models for specialized data categories:
- Court Records
- Business Filings
- Professional Licenses
- Federal Data (USPTO, SEC, FDIC, Census)
- News Articles

These models extend the base Record model with category-specific fields.
"""

from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, ForeignKey, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from datagod.models.base import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# =============================================================================
# Court Records
# =============================================================================

class CourtCaseRecord(Base, TimestampMixin):
    """
    Represents a court case record.
    Covers civil, criminal, family, probate, bankruptcy cases.
    """
    __tablename__ = 'court_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Case identification
    case_number = Column(String(100), nullable=False, index=True)
    case_type = Column(String(50), nullable=False, index=True)  # civil, criminal, family, etc.
    court_name = Column(String(255), nullable=True)
    case_title = Column(String(500), nullable=True)

    # Dates
    filing_date = Column(Date, nullable=True, index=True)
    disposition_date = Column(Date, nullable=True)

    # Status
    status = Column(String(50), default='open')  # open, closed, pending, dismissed, etc.
    disposition = Column(String(255), nullable=True)

    # Judge
    judge_name = Column(String(255), nullable=True)

    # Location
    county = Column(String(100), nullable=True, index=True)
    state = Column(String(2), nullable=True, index=True)

    # Financial
    amount_claimed = Column(Float, nullable=True)
    amount_awarded = Column(Float, nullable=True)

    # Parties (stored as JSON for flexibility)
    parties = Column(JSON, nullable=True)  # [{name, party_type, attorney, ...}, ...]

    # URLs
    url = Column(String(1000), nullable=True)
    document_url = Column(String(1000), nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_court_case_number', 'case_number'),
        Index('idx_court_case_type', 'case_type'),
        Index('idx_court_case_state_county', 'state', 'county'),
        Index('idx_court_case_filing_date', 'filing_date'),
        Index('idx_court_case_status', 'status'),
    )

    def __repr__(self):
        return f"<CourtCase(case_number='{self.case_number}', type='{self.case_type}')>"


# =============================================================================
# Business Filings
# =============================================================================

class BusinessEntityRecord(Base, TimestampMixin):
    """
    Represents a business entity record.
    Covers corporations, LLCs, partnerships, etc.
    """
    __tablename__ = 'business_entities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Entity identification
    entity_id = Column(String(100), nullable=False, index=True)  # State filing number
    entity_name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # corporation, llc, llp, etc.

    # Status
    status = Column(String(50), default='active', index=True)  # active, inactive, dissolved, etc.

    # Dates
    formation_date = Column(Date, nullable=True, index=True)
    dissolution_date = Column(Date, nullable=True)

    # Location
    state = Column(String(2), nullable=False, index=True)
    jurisdiction_of_formation = Column(String(100), nullable=True)

    # Registered agent
    registered_agent_name = Column(String(255), nullable=True)
    registered_agent_address = Column(String(500), nullable=True)

    # Addresses
    principal_address = Column(String(500), nullable=True)
    mailing_address = Column(String(500), nullable=True)

    # Officers/members (stored as JSON)
    officers = Column(JSON, nullable=True)  # [{name, title, address, ...}, ...]

    # Previous names
    previous_names = Column(JSON, nullable=True)  # [name1, name2, ...]

    # EIN
    ein = Column(String(20), nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_business_entity_id', 'entity_id'),
        Index('idx_business_entity_name', 'entity_name'),
        Index('idx_business_entity_type', 'entity_type'),
        Index('idx_business_entity_state', 'state'),
        Index('idx_business_entity_status', 'status'),
    )

    def __repr__(self):
        return f"<BusinessEntity(name='{self.entity_name}', type='{self.entity_type}')>"


class UCCFilingRecord(Base, TimestampMixin):
    """
    Represents a UCC (Uniform Commercial Code) filing.
    """
    __tablename__ = 'ucc_filings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Filing identification
    filing_number = Column(String(100), nullable=False, index=True)
    filing_type = Column(String(50), nullable=False)  # initial, amendment, termination, etc.

    # Dates
    filing_date = Column(Date, nullable=False, index=True)
    lapse_date = Column(Date, nullable=True)

    # Parties
    secured_party = Column(String(500), nullable=True, index=True)
    secured_party_address = Column(String(500), nullable=True)
    debtor_name = Column(String(500), nullable=True, index=True)
    debtor_address = Column(String(500), nullable=True)

    # Collateral
    collateral_description = Column(Text, nullable=True)

    # State
    state = Column(String(2), nullable=True, index=True)

    # Amendments (stored as JSON)
    amendments = Column(JSON, nullable=True)  # [{date, type, description, ...}, ...]

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_ucc_filing_number', 'filing_number'),
        Index('idx_ucc_filing_date', 'filing_date'),
        Index('idx_ucc_secured_party', 'secured_party'),
        Index('idx_ucc_debtor', 'debtor_name'),
        Index('idx_ucc_state', 'state'),
    )

    def __repr__(self):
        return f"<UCCFiling(filing_number='{self.filing_number}', debtor='{self.debtor_name}')>"


# =============================================================================
# Professional Licenses
# =============================================================================

class ProfessionalLicenseRecord(Base, TimestampMixin):
    """
    Represents a professional license record.
    Covers real estate, mortgage, attorneys, contractors, etc.
    """
    __tablename__ = 'professional_licenses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'), nullable=False)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # License identification
    license_number = Column(String(100), nullable=False, index=True)
    license_type = Column(String(100), nullable=False, index=True)  # real_estate_agent, attorney, etc.

    # Licensee information
    licensee_name = Column(String(500), nullable=False, index=True)
    licensee_type = Column(String(50), nullable=True)  # individual, business
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True, index=True)

    # Status
    status = Column(String(50), default='active', index=True)  # active, inactive, suspended, etc.

    # Dates
    issue_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True, index=True)
    original_issue_date = Column(Date, nullable=True)

    # Location
    state = Column(String(2), nullable=False, index=True)
    city = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)

    # Employer/firm
    employer_name = Column(String(500), nullable=True)
    employer_license = Column(String(100), nullable=True)

    # Specializations
    specializations = Column(JSON, nullable=True)  # [specialty1, specialty2, ...]

    # Disciplinary actions (stored as JSON)
    disciplinary_actions = Column(JSON, nullable=True)  # [{date, type, description, ...}, ...]

    # NMLS-specific (for mortgage professionals)
    nmls_id = Column(String(50), nullable=True, index=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_license_number', 'license_number'),
        Index('idx_license_type', 'license_type'),
        Index('idx_license_name', 'licensee_name'),
        Index('idx_license_last_name', 'last_name'),
        Index('idx_license_state', 'state'),
        Index('idx_license_status', 'status'),
        Index('idx_license_nmls', 'nmls_id'),
    )

    def __repr__(self):
        return f"<ProfessionalLicense(number='{self.license_number}', name='{self.licensee_name}')>"


# =============================================================================
# Federal Data - USPTO
# =============================================================================

class TrademarkRecord(Base, TimestampMixin):
    """
    Represents a USPTO trademark record.
    """
    __tablename__ = 'trademarks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Trademark identification
    serial_number = Column(String(50), nullable=False, unique=True, index=True)
    registration_number = Column(String(50), nullable=True, index=True)

    # Mark information
    mark_text = Column(String(500), nullable=True, index=True)
    mark_description = Column(Text, nullable=True)

    # Status
    status = Column(String(50), nullable=True, index=True)  # registered, pending, abandoned, etc.

    # Dates
    filing_date = Column(Date, nullable=True, index=True)
    registration_date = Column(Date, nullable=True)

    # Owner
    owner_name = Column(String(500), nullable=True, index=True)
    owner_address = Column(String(500), nullable=True)
    owner_type = Column(String(50), nullable=True)  # individual, corporation, etc.

    # Attorney
    attorney_name = Column(String(255), nullable=True)

    # Classification
    goods_services = Column(Text, nullable=True)
    international_classes = Column(JSON, nullable=True)  # [class1, class2, ...]
    design_search_codes = Column(JSON, nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_trademark_serial', 'serial_number'),
        Index('idx_trademark_registration', 'registration_number'),
        Index('idx_trademark_mark', 'mark_text'),
        Index('idx_trademark_owner', 'owner_name'),
        Index('idx_trademark_status', 'status'),
    )

    def __repr__(self):
        return f"<Trademark(serial='{self.serial_number}', mark='{self.mark_text}')>"


class PatentRecord(Base, TimestampMixin):
    """
    Represents a USPTO patent record.
    """
    __tablename__ = 'patents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Patent identification
    patent_number = Column(String(50), nullable=False, unique=True, index=True)
    application_number = Column(String(50), nullable=True, index=True)

    # Patent information
    title = Column(String(1000), nullable=True, index=True)
    abstract = Column(Text, nullable=True)
    patent_type = Column(String(50), nullable=True)  # utility, design, plant, etc.

    # Status
    status = Column(String(50), nullable=True, index=True)  # active, expired, pending, etc.

    # Dates
    filing_date = Column(Date, nullable=True, index=True)
    issue_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)

    # Inventors and assignees
    inventors = Column(JSON, nullable=True)  # [name1, name2, ...]
    assignee_name = Column(String(500), nullable=True, index=True)
    assignee_address = Column(String(500), nullable=True)

    # Claims
    claims_count = Column(Integer, nullable=True)

    # Classification
    classification_codes = Column(JSON, nullable=True)  # [code1, code2, ...]

    # Citations
    citations = Column(JSON, nullable=True)  # [patent1, patent2, ...]

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_patent_number', 'patent_number'),
        Index('idx_patent_application', 'application_number'),
        Index('idx_patent_title', 'title'),
        Index('idx_patent_assignee', 'assignee_name'),
        Index('idx_patent_status', 'status'),
    )

    def __repr__(self):
        return f"<Patent(number='{self.patent_number}', title='{self.title[:50]}...')>"


# =============================================================================
# Federal Data - SEC
# =============================================================================

class SECFilingRecord(Base, TimestampMixin):
    """
    Represents an SEC EDGAR filing record.
    """
    __tablename__ = 'sec_filings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Filing identification
    accession_number = Column(String(50), nullable=False, unique=True, index=True)
    form_type = Column(String(20), nullable=False, index=True)  # 10-K, 10-Q, 8-K, etc.

    # Company information
    cik = Column(String(20), nullable=False, index=True)
    company_name = Column(String(500), nullable=True, index=True)
    ticker = Column(String(20), nullable=True, index=True)

    # Dates
    filing_date = Column(Date, nullable=False, index=True)
    accepted_datetime = Column(DateTime, nullable=True)
    period_of_report = Column(Date, nullable=True)

    # Document information
    document_url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)

    # Company details
    sic_code = Column(String(10), nullable=True)
    sic_description = Column(String(255), nullable=True)
    state = Column(String(2), nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_sec_accession', 'accession_number'),
        Index('idx_sec_form_type', 'form_type'),
        Index('idx_sec_cik', 'cik'),
        Index('idx_sec_company', 'company_name'),
        Index('idx_sec_ticker', 'ticker'),
        Index('idx_sec_filing_date', 'filing_date'),
    )

    def __repr__(self):
        return f"<SECFiling(accession='{self.accession_number}', form='{self.form_type}')>"


# =============================================================================
# Federal Data - FDIC
# =============================================================================

class BankRecord(Base, TimestampMixin):
    """
    Represents an FDIC-insured bank record.
    """
    __tablename__ = 'banks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Bank identification
    fdic_cert = Column(String(20), nullable=False, unique=True, index=True)
    bank_name = Column(String(500), nullable=False, index=True)

    # Status
    status = Column(String(50), default='active', index=True)  # active, inactive, failed, merged

    # Charter
    charter_type = Column(String(50), nullable=True)

    # Location
    headquarters_city = Column(String(100), nullable=True)
    headquarters_state = Column(String(2), nullable=True, index=True)
    headquarters_address = Column(String(500), nullable=True)

    # Dates
    established_date = Column(Date, nullable=True)
    insured_date = Column(Date, nullable=True)

    # Financials
    total_assets = Column(Float, nullable=True)
    total_deposits = Column(Float, nullable=True)

    # Structure
    branches_count = Column(Integer, default=0)
    holding_company = Column(String(500), nullable=True)

    # Regulator
    primary_regulator = Column(String(50), nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_bank_fdic_cert', 'fdic_cert'),
        Index('idx_bank_name', 'bank_name'),
        Index('idx_bank_state', 'headquarters_state'),
        Index('idx_bank_status', 'status'),
    )

    def __repr__(self):
        return f"<Bank(fdic_cert='{self.fdic_cert}', name='{self.bank_name}')>"


# =============================================================================
# News Articles
# =============================================================================

class NewsArticleRecord(Base, TimestampMixin):
    """
    Represents a news article record.
    """
    __tablename__ = 'news_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Article identification
    article_id = Column(String(255), nullable=False, index=True)  # External article ID or hash
    url = Column(String(1000), nullable=True, unique=True)

    # Content
    title = Column(String(1000), nullable=False, index=True)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    # Source
    source_name = Column(String(255), nullable=True, index=True)
    source_type = Column(String(50), nullable=True)  # major_outlet, local_news, wire_service, etc.

    # Dates
    published_at = Column(DateTime, nullable=False, index=True)

    # Location (for local news)
    state = Column(String(2), nullable=True, index=True)
    city = Column(String(100), nullable=True)

    # Category and sentiment
    category = Column(String(50), nullable=True, index=True)  # business, legal, real_estate, etc.
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral

    # Extracted data
    keywords = Column(JSON, nullable=True)  # [keyword1, keyword2, ...]
    entities_mentioned = Column(JSON, nullable=True)  # [entity1, entity2, ...]
    locations_mentioned = Column(JSON, nullable=True)  # [location1, location2, ...]

    # Image
    image_url = Column(String(1000), nullable=True)

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_news_article_id', 'article_id'),
        Index('idx_news_title', 'title'),
        Index('idx_news_source', 'source_name'),
        Index('idx_news_published', 'published_at'),
        Index('idx_news_state', 'state'),
        Index('idx_news_category', 'category'),
    )

    def __repr__(self):
        return f"<NewsArticle(title='{self.title[:50]}...', source='{self.source_name}')>"


class PressReleaseRecord(Base, TimestampMixin):
    """
    Represents a press release record.
    """
    __tablename__ = 'press_releases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(Integer, ForeignKey('data_sources.id'), nullable=True)

    # Release identification
    release_id = Column(String(255), nullable=False, index=True)
    url = Column(String(1000), nullable=True, unique=True)

    # Content
    headline = Column(String(1000), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)

    # Source company
    source_company = Column(String(500), nullable=False, index=True)

    # Dates
    published_at = Column(DateTime, nullable=False, index=True)

    # Contact
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)

    # Tickers and topics
    ticker_symbols = Column(JSON, nullable=True)  # [AAPL, GOOGL, ...]
    topics = Column(JSON, nullable=True)  # [topic1, topic2, ...]

    # Wire service
    wire_service = Column(String(100), nullable=True)  # PRNewswire, BusinessWire, etc.

    # Raw data
    raw_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_press_release_id', 'release_id'),
        Index('idx_press_headline', 'headline'),
        Index('idx_press_company', 'source_company'),
        Index('idx_press_published', 'published_at'),
    )

    def __repr__(self):
        return f"<PressRelease(headline='{self.headline[:50]}...', company='{self.source_company}')>"
