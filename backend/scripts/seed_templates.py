"""Seed the clause_templates table with market-standard clauses."""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add backend to path so imports work
sys.path.insert(0, ".")

from app.core.config import settings
from app.models.clause_template import ClauseTemplate
from app.services.embedding import generate_embeddings_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Market-standard clause templates organized by contract type
TEMPLATES = [
    # ---- NDA Templates ----
    {
        "contract_type": "nda",
        "clause_type": "definition_of_confidential_info",
        "standard_text": (
            '"Confidential Information" means any non-public information disclosed '
            "by either party to the other, whether orally, in writing, or by inspection, "
            "including but not limited to business plans, financial data, technical data, "
            "trade secrets, and know-how. Confidential Information does not include "
            "information that: (a) is or becomes publicly available through no fault of "
            "the receiving party; (b) was known to the receiving party prior to disclosure; "
            "(c) is independently developed without use of the disclosing party's "
            "Confidential Information; or (d) is rightfully received from a third party "
            "without restriction."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "confidentiality",
        "standard_text": (
            "The Receiving Party agrees to: (a) hold the Confidential Information in "
            "strict confidence using the same degree of care it uses for its own "
            "confidential information, but no less than reasonable care; (b) not disclose "
            "the Confidential Information to any third party without the prior written "
            "consent of the Disclosing Party, except to its employees, contractors, and "
            "advisors who need to know and are bound by confidentiality obligations at "
            "least as protective as those herein; and (c) use the Confidential Information "
            "solely for the purpose of evaluating or pursuing a business relationship "
            "between the parties."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "exclusions",
        "standard_text": (
            "The obligations of confidentiality shall not apply to information that: "
            "(a) is or becomes publicly available through no fault of the Receiving Party; "
            "(b) was rightfully in the Receiving Party's possession prior to disclosure; "
            "(c) is independently developed by the Receiving Party without reference to "
            "the Confidential Information; or (d) is rightfully obtained from a third party "
            "without restriction on disclosure."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "non_compete",
        "standard_text": (
            "During the term of this Agreement and for a period of twelve (12) months "
            "following its termination, the Receiving Party shall not directly use the "
            "Confidential Information to engage in any business that is in direct "
            "competition with the specific products or services of the Disclosing Party "
            "that are the subject of this Agreement, within the geographic areas where "
            "the Disclosing Party actively conducts such business. This restriction shall "
            "not apply to activities conducted without use of the Confidential Information "
            "or to passive investments of less than 5% in publicly traded companies."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "non_solicitation",
        "standard_text": (
            "For a period of twelve (12) months following termination of this Agreement, "
            "neither party shall directly solicit for employment any employee of the other "
            "party with whom it had material contact in connection with this Agreement. "
            "This restriction shall not apply to general solicitations of employment not "
            "specifically directed at such employees, or to any person whose employment "
            "with the other party ended at least six (6) months prior to solicitation."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "indemnification",
        "standard_text": (
            "Each party shall indemnify, defend, and hold harmless the other party from "
            "and against any third-party claims, losses, damages, liabilities, and "
            "reasonable expenses (including attorneys' fees) arising out of or relating to "
            "the indemnifying party's breach of this Agreement or gross negligence. The "
            "indemnified party shall promptly notify the indemnifying party of any such "
            "claim and cooperate in its defense. The indemnifying party's total aggregate "
            "liability shall not exceed the greater of actual direct damages or $50,000."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "termination",
        "standard_text": (
            "This Agreement shall remain in effect for a period of two (2) years from "
            "the Effective Date, unless terminated earlier by either party upon thirty (30) "
            "days' written notice. Either party may terminate immediately upon written "
            "notice if the other party materially breaches this Agreement and fails to "
            "cure such breach within fifteen (15) days of receiving written notice. "
            "Confidentiality obligations shall survive termination for a period of three "
            "(3) years."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "return_of_materials",
        "standard_text": (
            "Upon termination of this Agreement or upon written request by the Disclosing "
            "Party, the Receiving Party shall promptly return or destroy all Confidential "
            "Information and certify in writing that it has done so. The Receiving Party "
            "may retain one archival copy solely for legal compliance purposes and copies "
            "on routine electronic backup systems that will be deleted in accordance with "
            "standard retention policies. Any retained information remains subject to "
            "this Agreement."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "governing_law",
        "standard_text": (
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the State of [State], without regard to its conflict of laws "
            "provisions. Any dispute arising under this Agreement shall be submitted to "
            "the non-exclusive jurisdiction of the state or federal courts located in "
            "[County, State]. Each party waives any objection based on inconvenient forum."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "limitation_of_liability",
        "standard_text": (
            "Except for breaches of confidentiality obligations, gross negligence, or "
            "willful misconduct, neither party shall be liable for any indirect, "
            "incidental, special, consequential, or punitive damages arising out of this "
            "Agreement. Each party's total aggregate liability shall not exceed the greater "
            "of actual direct damages sustained or $10,000."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "entire_agreement",
        "standard_text": (
            "This Agreement constitutes the entire agreement between the parties with "
            "respect to the subject matter hereof and supersedes all prior agreements, "
            "understandings, and representations. This Agreement may not be amended except "
            "by a written instrument signed by both parties. Any waiver must be in writing "
            "and signed by the waiving party."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "assignment",
        "standard_text": (
            "Neither party may assign this Agreement without the prior written consent of "
            "the other party, which consent shall not be unreasonably withheld. "
            "Notwithstanding the foregoing, either party may assign this Agreement without "
            "consent to an affiliate or to a successor in connection with a merger, "
            "acquisition, or sale of all or substantially all of its assets. Any attempted "
            "assignment in violation of this section shall be void."
        ),
        "source": "Market standard NDA template",
    },
    {
        "contract_type": "nda",
        "clause_type": "severability",
        "standard_text": (
            "If any provision of this Agreement is held to be invalid or unenforceable, "
            "the remaining provisions shall continue in full force and effect. The invalid "
            "provision shall be modified to the minimum extent necessary to make it valid "
            "and enforceable while preserving the parties' original intent."
        ),
        "source": "Market standard NDA template",
    },
    # ---- MSA Templates ----
    {
        "contract_type": "msa",
        "clause_type": "scope_of_services",
        "standard_text": (
            "The Service Provider shall perform the services described in each Statement "
            "of Work (SOW) executed under this Agreement. Each SOW shall specify the scope, "
            "deliverables, timeline, acceptance criteria, and fees. In the event of a "
            "conflict between this Agreement and any SOW, this Agreement shall prevail "
            "unless the SOW expressly states otherwise."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "payment_terms",
        "standard_text": (
            "Client shall pay all undisputed invoices within thirty (30) days of receipt. "
            "Late payments shall accrue interest at the lesser of 1.5% per month or the "
            "maximum rate permitted by law. Client may dispute any invoice in good faith "
            "by providing written notice within fifteen (15) days of receipt, specifying "
            "the disputed amount and reason."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "intellectual_property",
        "standard_text": (
            "All pre-existing intellectual property remains the property of the party that "
            "owned it prior to this Agreement. Work product created specifically for Client "
            "under a SOW shall be owned by Client upon full payment. Service Provider "
            "retains ownership of its tools, methodologies, and general knowledge gained "
            "during performance, and grants Client a perpetual, non-exclusive license to "
            "use any such materials incorporated into deliverables."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "warranties",
        "standard_text": (
            "Service Provider warrants that: (a) services will be performed in a "
            "professional and workmanlike manner consistent with industry standards; "
            "(b) deliverables will materially conform to the specifications in the "
            "applicable SOW for a period of thirty (30) days following acceptance; and "
            "(c) it has the right and authority to enter into this Agreement. Except as "
            "expressly stated herein, all other warranties are disclaimed."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "indemnification",
        "standard_text": (
            "Each party shall indemnify the other against third-party claims arising from: "
            "(a) the indemnifying party's breach of this Agreement; (b) the indemnifying "
            "party's negligence or willful misconduct; or (c) infringement of intellectual "
            "property rights by materials provided by the indemnifying party. The "
            "indemnified party shall provide prompt notice and reasonable cooperation."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "limitation_of_liability",
        "standard_text": (
            "Neither party shall be liable for indirect, incidental, special, "
            "consequential, or punitive damages. Each party's total aggregate liability "
            "under this Agreement shall not exceed the total fees paid or payable in the "
            "twelve (12) months preceding the claim. These limitations shall not apply to "
            "breaches of confidentiality, indemnification obligations, or willful misconduct."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "termination",
        "standard_text": (
            "Either party may terminate this Agreement: (a) for convenience upon sixty "
            "(60) days' written notice; or (b) for cause if the other party materially "
            "breaches and fails to cure within thirty (30) days of written notice. Upon "
            "termination, Client shall pay for all services performed and accepted through "
            "the termination date. Sections relating to confidentiality, indemnification, "
            "limitation of liability, and intellectual property shall survive termination."
        ),
        "source": "Market standard MSA template",
    },
    {
        "contract_type": "msa",
        "clause_type": "confidentiality",
        "standard_text": (
            "Each party agrees to maintain the confidentiality of the other party's "
            "proprietary information using the same degree of care it uses for its own "
            "confidential information, but no less than reasonable care. Confidential "
            "Information may be disclosed to employees and contractors who need to know "
            "and are bound by obligations at least as protective. Confidentiality "
            "obligations shall survive for three (3) years following disclosure."
        ),
        "source": "Market standard MSA template",
    },
    # ---- SOW Templates ----
    {
        "contract_type": "sow",
        "clause_type": "scope_of_work",
        "standard_text": (
            "This Statement of Work describes the specific services to be performed under "
            "the Master Service Agreement dated [Date]. The scope includes: [description]. "
            "Any work outside this scope requires a written change order signed by both "
            "parties before work begins."
        ),
        "source": "Market standard SOW template",
    },
    {
        "contract_type": "sow",
        "clause_type": "deliverables",
        "standard_text": (
            "Service Provider shall deliver the following deliverables according to the "
            "timeline specified: [list]. Each deliverable shall be subject to Client's "
            "review and acceptance within ten (10) business days of delivery. If Client "
            "does not provide written notice of rejection within the acceptance period, "
            "the deliverable shall be deemed accepted."
        ),
        "source": "Market standard SOW template",
    },
    {
        "contract_type": "sow",
        "clause_type": "timeline",
        "standard_text": (
            "The project shall commence on [Start Date] and is expected to be completed "
            "by [End Date]. Milestones are set forth in the project schedule attached as "
            "Exhibit A. Delays caused by Client (including late feedback or resource "
            "unavailability) shall extend the timeline by an equivalent period. Material "
            "changes to the timeline require a written change order."
        ),
        "source": "Market standard SOW template",
    },
    {
        "contract_type": "sow",
        "clause_type": "payment_terms",
        "standard_text": (
            "Fees for this SOW are [amount] payable as follows: [schedule]. Invoices are "
            "due within thirty (30) days of receipt. Expenses must be pre-approved in "
            "writing and will be reimbursed at cost. If the project is terminated early, "
            "Client shall pay for all work completed and accepted through the termination "
            "date plus any non-cancellable commitments."
        ),
        "source": "Market standard SOW template",
    },
    {
        "contract_type": "sow",
        "clause_type": "change_order",
        "standard_text": (
            "Any changes to the scope, deliverables, timeline, or fees must be documented "
            "in a written change order signed by authorized representatives of both parties "
            "before work on the change begins. Change orders shall specify the impact on "
            "fees, timeline, and deliverables. Verbal change requests are not binding."
        ),
        "source": "Market standard SOW template",
    },
    {
        "contract_type": "sow",
        "clause_type": "acceptance_criteria",
        "standard_text": (
            "Deliverables shall be evaluated against the acceptance criteria defined in "
            "this SOW. Client shall review each deliverable within ten (10) business days "
            "and provide written acceptance or a detailed rejection specifying deficiencies. "
            "Service Provider shall have fifteen (15) business days to cure any deficiencies. "
            "If deficiencies are not cured after two rounds of revision, either party may "
            "escalate per the dispute resolution process."
        ),
        "source": "Market standard SOW template",
    },
    # ---- Freelance Agreement Templates ----
    {
        "contract_type": "freelance",
        "clause_type": "scope_of_services",
        "standard_text": (
            "Contractor shall perform the services described in Exhibit A. Contractor "
            "shall have discretion over the manner and means of performing the services, "
            "provided that the work meets the specifications and deadlines agreed upon. "
            "Any additional services beyond the agreed scope require written approval and "
            "may be subject to additional fees."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "compensation",
        "standard_text": (
            "Client shall pay Contractor [rate/amount] for services rendered. Invoices "
            "shall be submitted [frequency] and are due within thirty (30) days of receipt. "
            "Contractor is responsible for all taxes, insurance, and benefits. Late "
            "payments shall accrue interest at 1.5% per month or the maximum rate "
            "permitted by law, whichever is less."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "independent_contractor",
        "standard_text": (
            "Contractor is an independent contractor, not an employee, agent, or partner "
            "of Client. Contractor shall not be entitled to any employee benefits. "
            "Contractor retains the right to perform services for other clients, provided "
            "there is no conflict of interest. Contractor is responsible for providing "
            "their own equipment and workspace unless otherwise agreed."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "intellectual_property",
        "standard_text": (
            "All work product created by Contractor specifically for Client under this "
            "Agreement shall be considered work made for hire and owned by Client upon "
            "full payment. To the extent any work product does not qualify as work made "
            "for hire, Contractor hereby assigns all rights to Client upon full payment. "
            "Contractor retains the right to use general skills, knowledge, and experience "
            "gained during the engagement, and may include the work in their portfolio "
            "unless Client requests otherwise in writing."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "termination",
        "standard_text": (
            "Either party may terminate this Agreement upon fourteen (14) days' written "
            "notice. Client may terminate immediately for cause if Contractor materially "
            "breaches and fails to cure within seven (7) days. Upon termination, Client "
            "shall pay for all completed and accepted work through the termination date. "
            "Contractor shall deliver all work-in-progress upon termination."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "confidentiality",
        "standard_text": (
            "Contractor agrees to maintain the confidentiality of Client's proprietary "
            "information and shall not disclose it to any third party without prior written "
            "consent. This obligation survives termination for a period of two (2) years. "
            "Confidential Information does not include information that is publicly "
            "available, independently developed, or rightfully received from a third party."
        ),
        "source": "Market standard freelance agreement template",
    },
    {
        "contract_type": "freelance",
        "clause_type": "limitation_of_liability",
        "standard_text": (
            "Neither party shall be liable for indirect, incidental, or consequential "
            "damages. Contractor's total liability shall not exceed the total fees paid "
            "under this Agreement in the six (6) months preceding the claim. Client's "
            "liability for unpaid fees is not subject to this limitation."
        ),
        "source": "Market standard freelance agreement template",
    },
    # ---- Lease Agreement Templates ----
    {
        "contract_type": "lease",
        "clause_type": "premises",
        "standard_text": (
            "Landlord hereby leases to Tenant the premises located at [Address] (the "
            '"Premises"), consisting of approximately [square footage] square feet, for '
            "the permitted use described herein. The Premises are leased in their current "
            '"as-is" condition, and Tenant acknowledges having inspected and accepted the '
            "condition of the Premises."
        ),
        "source": "Market standard lease agreement template",
    },
    {
        "contract_type": "lease",
        "clause_type": "rent",
        "standard_text": (
            "Tenant shall pay monthly rent of [amount] due on the first day of each month. "
            "Rent paid more than five (5) days late shall incur a late fee of [amount or "
            "percentage]. Rent shall increase annually by [percentage or CPI adjustment]. "
            "All payments shall be made to Landlord at [address or account]."
        ),
        "source": "Market standard lease agreement template",
    },
    {
        "contract_type": "lease",
        "clause_type": "security_deposit",
        "standard_text": (
            "Tenant shall provide a security deposit of [amount] upon execution of this "
            "Lease. The deposit shall be held by Landlord and returned within thirty (30) "
            "days of lease termination, less any amounts deducted for unpaid rent, damages "
            "beyond normal wear and tear, or cleaning costs. Landlord shall provide an "
            "itemized statement of any deductions."
        ),
        "source": "Market standard lease agreement template",
    },
    {
        "contract_type": "lease",
        "clause_type": "maintenance",
        "standard_text": (
            "Landlord shall be responsible for structural repairs and maintenance of "
            "building systems (HVAC, plumbing, electrical). Tenant shall maintain the "
            "interior of the Premises in good condition and promptly report any needed "
            "repairs. Tenant is responsible for minor repairs and routine maintenance "
            "up to [amount] per occurrence."
        ),
        "source": "Market standard lease agreement template",
    },
    {
        "contract_type": "lease",
        "clause_type": "termination",
        "standard_text": (
            "This Lease shall commence on [Start Date] and terminate on [End Date]. "
            "Either party may terminate upon sixty (60) days' written notice at the end "
            "of any lease year. Landlord may terminate immediately if Tenant fails to pay "
            "rent within ten (10) days of written notice or materially breaches any term. "
            "Upon termination, Tenant shall vacate and return the Premises in good "
            "condition, normal wear and tear excepted."
        ),
        "source": "Market standard lease agreement template",
    },
    {
        "contract_type": "lease",
        "clause_type": "assignment",
        "standard_text": (
            "Tenant shall not assign this Lease or sublease any portion of the Premises "
            "without Landlord's prior written consent, which shall not be unreasonably "
            "withheld, conditioned, or delayed. Any approved assignment or sublease shall "
            "not release Tenant from its obligations under this Lease unless Landlord "
            "agrees in writing."
        ),
        "source": "Market standard lease agreement template",
    },
]


def seed_templates() -> None:
    """Seed the clause_templates table with market-standard clauses."""
    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    session = Session(engine)

    try:
        # Check if templates already exist
        existing_count = session.query(ClauseTemplate).count()
        if existing_count > 0:
            logger.info(
                "Found %d existing templates. Clearing and re-seeding.",
                existing_count,
            )
            session.query(ClauseTemplate).delete()
            session.commit()

        # Generate embeddings for all template texts in batch
        texts = [t["standard_text"] for t in TEMPLATES]
        logger.info("Generating embeddings for %d templates...", len(texts))
        embeddings = generate_embeddings_batch(texts)
        logger.info("Embeddings generated successfully.")

        # Insert templates with embeddings
        for template_data, embedding in zip(TEMPLATES, embeddings, strict=True):
            template = ClauseTemplate(
                id=uuid.uuid4(),
                contract_type=template_data["contract_type"],
                clause_type=template_data["clause_type"],
                standard_text=template_data["standard_text"],
                embedding=embedding,
                source=template_data.get("source"),
                created_at=datetime.now(UTC),
            )
            session.add(template)

        session.commit()
        logger.info("Successfully seeded %d clause templates.", len(TEMPLATES))

        # Print summary
        from collections import Counter

        type_counts = Counter(t["contract_type"] for t in TEMPLATES)
        for contract_type, count in sorted(type_counts.items()):
            logger.info("  %s: %d templates", contract_type, count)

    except Exception:
        logger.exception("Failed to seed templates")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    seed_templates()
