---
title: IIIF Studio
emoji: 📜
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# IIIF Studio

Plateforme générique de génération d'éditions savantes augmentées pour documents
patrimoniaux numérisés : manuscrits médiévaux, incunables, cartulaires, archives,
chartes, papyri — tout type de document, toute époque, toute langue.

---

## Structure du dépôt

```
iiif-studio/
├── backend/            # API FastAPI + pipeline Python
│   ├── app/
│   │   ├── api/v1/     # endpoints REST (/api/v1/...)
│   │   ├── models/     # tables SQLAlchemy (SQLite async)
│   │   ├── schemas/    # modèles Pydantic v2
│   │   └── services/   # ingest / image / ai / export / search
│   ├── tests/          # suite pytest (563 tests)
│   └── pyproject.toml
├── frontend/           # React + TypeScript + Vite (design rétro)
├── profiles/           # 4 profils de corpus JSON
├── prompts/            # templates de prompts par profil
├── infra/              # docker-compose (dev local)
├── Dockerfile          # image multi-stage (frontend + backend)
└── data/               # artefacts runtime — NON versionné
```

---

## Lancer en local (Docker)

```bash
# 1. Cloner le dépôt
git clone https://github.com/<org>/iiif-studio && cd iiif-studio

# 2. Définir les variables d'environnement
cp .env.example .env          # puis renseigner les clés dans .env

# 3. Démarrer le service
docker compose -f infra/docker-compose.yml up --build

# 4. Vérifier
curl http://localhost:7860/api/v1/profiles
```

L'API est accessible sur `http://localhost:7860`. La documentation interactive
Swagger est disponible sur `http://localhost:7860/docs`.

---

## Lancer les tests

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v --cov=app
```

Résultat attendu : **563 passed, 3 skipped**.

---

## Profils disponibles

| Profil | Description |
|--------|-------------|
| `medieval-illuminated` | Manuscrits médiévaux enluminés (OCR diplomatique, iconographie, commentaire) |
| `medieval-textual`     | Manuscrits médiévaux textuels (OCR, traduction, commentaire savant) |
| `early-modern-print`   | Imprimés anciens (incunables, livres des XVIe–XVIIIe siècles) |
| `modern-handwritten`   | Documents manuscrits modernes (cursive, archives, chartes) |

```bash
# Lister les profils via l'API
curl http://localhost:7860/api/v1/profiles
```

---

## Providers IA

Le backend détecte automatiquement quels providers sont disponibles selon les
variables d'environnement présentes. Pas de sélecteur global `AI_PROVIDER` —
le modèle est choisi par corpus depuis l'interface d'administration.

| Provider | Variable d'environnement |
|----------|--------------------------|
| Google AI Studio | `GOOGLE_AI_STUDIO_API_KEY` |
| Vertex AI (clé API) | `VERTEX_API_KEY` |
| Vertex AI (compte de service) | `VERTEX_SERVICE_ACCOUNT_JSON` |
| Mistral AI | `MISTRAL_API_KEY` |

Au moins **une** clé est nécessaire pour que le pipeline fonctionne.

Les clés ne doivent **jamais** figurer dans le code, les commits ou l'image Docker.
Sur HuggingFace Spaces, les renseigner dans **Settings → Repository secrets**.

---

## Déploiement HuggingFace Spaces

Ce dépôt est configuré pour HuggingFace Spaces (SDK Docker, port 7860).
Les artefacts de traitement (images, JSON maîtres, exports XML) sont stockés
sur HuggingFace Datasets — pas dans l'image Docker.

Voir `.huggingface/README.md` pour la configuration spécifique du Space.
