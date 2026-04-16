"""
Exécution séquentielle du pipeline sur tous les jobs d'un corpus (Sprint 4 — Session C).

Point d'entrée : execute_corpus_job(corpus_id)
  → récupère tous les jobs PENDING du corpus
  → les exécute séquentiellement (pas de parallélisme au MVP)
  → retourne un résumé {total, done, failed}

Chaque page reçoit sa propre session pour isoler les échecs.
"""
# 1. stdlib
import asyncio
import logging

# 2. third-party
from sqlalchemy import select

# 3. local
from app.models.database import async_session_factory
from app.models.job import JobModel

logger = logging.getLogger(__name__)


async def execute_corpus_job(corpus_id: str) -> dict:
    """Lance tous les jobs PENDING du corpus séquentiellement.

    Chaque job est exécuté dans sa propre session (isolement des échecs).
    Un job FAILED n'interrompt pas les suivants.

    Returns:
        {"total": int, "done": int, "failed": int}
    """
    # Collecte et verrouillage des jobs PENDING : on les passe immédiatement
    # en "claimed" pour éviter qu'un second appel concurrent ne les reprenne
    # (TOCTOU). Chaque job sera ensuite passé en "running" par job_runner.
    async with async_session_factory() as db:
        result = await db.execute(
            select(JobModel).where(
                JobModel.corpus_id == corpus_id,
                JobModel.status == "pending",
            )
        )
        pending_jobs = list(result.scalars().all())
        job_ids: list[str] = [j.id for j in pending_jobs]
        for j in pending_jobs:
            j.status = "claimed"
        await db.commit()

    if not job_ids:
        logger.info(
            "Corpus run : aucun job pending",
            extra={"corpus_id": corpus_id},
        )
        return {"total": 0, "done": 0, "failed": 0}

    logger.info(
        "Corpus run démarré",
        extra={"corpus_id": corpus_id, "jobs": len(job_ids)},
    )

    # Exécution concurrente avec semaphore — chaque job gère sa propre session
    from app.services.job_runner import execute_page_job
    from app.config import settings

    sem = asyncio.Semaphore(settings.ai_max_concurrent)

    async def _run_one(jid: str) -> None:
        async with sem:
            await execute_page_job(jid)

    await asyncio.gather(*[_run_one(jid) for jid in job_ids])

    # Bilan final
    async with async_session_factory() as db:
        result = await db.execute(
            select(JobModel).where(JobModel.id.in_(job_ids))
        )
        jobs = list(result.scalars().all())

    done = sum(1 for j in jobs if j.status == "done")
    failed = sum(1 for j in jobs if j.status == "failed")
    total = len(job_ids)

    logger.info(
        "Corpus run terminé",
        extra={
            "corpus_id": corpus_id,
            "total": total,
            "done": done,
            "failed": failed,
        },
    )
    return {"total": total, "done": done, "failed": failed}
