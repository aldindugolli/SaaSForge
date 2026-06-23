from app.core.extensions import rq
from app.knowledge.services import KnowledgeService


def _job(queue):
    if rq is None:
        return lambda f: f
    return rq.job(queue)


@_job("saasforge-jobs")
def process_document_job(doc_id: str):
    return KnowledgeService.process_document(doc_id)


@_job("saasforge-jobs")
def reprocess_document_job(doc_id: str):
    doc = __import__("app.knowledge.models", fromlist=["KnowledgeDocument"]).KnowledgeDocument.query.get(doc_id)
    if doc:
        doc.embedding_status = "pending"
        __import__("app.core.extensions", fromlist=["db"]).db.session.commit()
    return KnowledgeService.process_document(doc_id)
