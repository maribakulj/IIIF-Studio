STATUS.md — Sprint 2 : Pipeline page unique
Sprint : 2 — Session A
Objectif du sprint : 1 image → 1 master.json valide via Google AI

Ce qui est fait (Sprint 1 ✓)

 Repo GitHub structuré, arborescence complète
 Schémas Pydantic : corpus_profile.py, page_master.py, annotation.py
 4 profils JSON (medieval-illuminated, medieval-textual, early-modern-print, modern-handwritten)
 9 templates de prompts versionnés
 54 tests pytest passants (26 schemas + 28 profiles)
 pyproject.toml configuré
 6 secrets GitHub en place :
GOOGLE_AI_STUDIO_API_KEY, VERTEX_API_KEY, VERTEX_PROJECT_ID,
VERTEX_LOCATION, VERTEX_SERVICE_ACCOUNT_JSON, AI_PROVIDER


Contexte important pour ce sprint
Providers Google AI disponibles
Trois options configurées, priorité :

AI_PROVIDER=vertex_api_key → clé AQ.Ab... (Vertex Express, production)
AI_PROVIDER=google_ai_studio → clé AIza... (gratuit, développement)
AI_PROVIDER=vertex_service_account → JSON credentials (institutions)

Format de clé Vertex non confirmé
La clé Vertex commence par AQ.Ab (format OAuth2 Vertex Express).
La syntaxe SDK exacte pour ce format N'EST PAS encore validée.
La Session A commence par ce test — avant tout le reste.
Images test disponibles
Pas d'images locales. On travaille avec des URLs IIIF directes.
URL Beatus haute résolution (profil medieval-illuminated) :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/full/0/native.jpg
URL Beatus basse résolution (même folio, qualité réduite — test confidence) :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/600,/0/native.jpg
URL second corpus — Grandes Chroniques de France (profil medieval-textual) :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b84472995/f16/full/full/0/native.jpg
Pourquoi tester deux résolutions du Beatus :
Les deux images doivent produire un master.json valide.
La basse résolution doit retourner un score confidence plus faible
et potentiellement déclencher le statut needs_review si < flag_below (0.4).
Cela valide que les seuils du profil fonctionnent correctement.

Session A — Connexion Google AI + listage modèles
Objectif
Valider que les 3 providers fonctionnent et lister les modèles disponibles.
Aucun traitement d'image. Aucun master.json. Juste la connexion.
Tâches dans l'ordre

Créer backend/app/services/ai/init.py (vide)
Créer backend/app/services/ai/client.py
→ factory get_ai_client() avec les 3 options
→ Option B (vertex_api_key) : tester les deux syntaxes possibles
et documenter celle qui fonctionne dans un commentaire
Créer backend/app/services/ai/models.py
→ fonction list_available_models(client) → list[dict]
→ filtrer sur les modèles qui supportent generateContent + vision
→ retourner : id, display_name, supports_vision
Créer backend/tests/test_ai_connection.py
→ test_option_a_google_ai_studio() : connexion + list_models
→ test_option_b_vertex_api_key() : connexion + list_models
→ test_option_c_vertex_service_account() : connexion + list_models
→ Chaque test affiche les modèles disponibles dans les logs
Lancer pytest test_ai_connection.py
→ documenter dans DECISIONS.md la syntaxe exacte validée pour AQ.Ab

Critère de done Session A
Les 3 tests de connexion passent.
On sait quelle syntaxe fonctionne pour la clé AQ.Ab.
La liste des modèles disponibles est affichée pour chaque provider.
Ne pas faire en Session A

Aucun traitement d'image
Aucun appel de prompt
Aucune ingestion de corpus


Session B — Ingestion + préparation image
Objectif
Ingérer une image depuis une URL IIIF et produire un dérivé web prêt pour l'IA.
Tâches dans l'ordre

Créer backend/app/services/ingest/init.py
Créer backend/app/services/ingest/image_loader.py
→ load_from_url(url) → image bytes + dimensions
→ load_from_file(path) → image bytes + dimensions
→ Pillow pour lire et redimensionner
Créer backend/app/services/image/init.py
Créer backend/app/services/image/processor.py
→ make_derivative(image_bytes, max_size=1500) → JPEG bytes
→ get_dimensions(image_bytes) → (width, height)
Tester sur les 3 URLs dans l'ordre :

Beatus haute résolution :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/full/0/native.jpg
Beatus basse résolution :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b52505441p/f233/full/600,/0/native.jpg
Grandes Chroniques :
https://gallica.bnf.fr/iiif/ark:/12148/btv1b84472995/f16/full/full/0/native.jpg
→ vérifier que les 3 images se téléchargent et se redimensionnent
→ vérifier que les dimensions sont bien extraites pour chaque cas


Ajouter tests/test_image_processing.py

Critère de done Session B
Les 3 URLs produisent chacune un JPEG dérivé de 1500px max.
Les dimensions sont correctement extraites pour chaque image.
La basse résolution Beatus produit bien une image plus petite en entrée.

Session C — Premier appel IA + master.json
Objectif
1 image → 1 appel Google AI → 1 master.json valide.
C'est le cœur du Sprint 2.
Tâches dans l'ordre

Créer backend/app/services/ai/prompt_loader.py
→ load_and_render(template_path, context_dict) → str
→ remplace {{profile_label}}, {{language_hints}}, {{script_type}}
Créer backend/app/services/ai/pipeline.py
→ analyze_page(image_bytes, corpus_profile, model_id) → PageMaster
→ Appelle le prompt primary_v1.txt du profil
→ Stocke ai_raw.json (brut) + master.json (validé Pydantic)
→ Lève une erreur explicite si le JSON retourné est invalide
Tester sur les 3 images dans l'ordre :
a. Beatus haute résolution + profil medieval-illuminated
→ master.json valide, confidence attendue > 0.6
b. Beatus basse résolution + profil medieval-illuminated
→ master.json valide, confidence attendue plus faible
→ vérifier que editorial.status = "needs_review" si confidence < 0.4
c. Grandes Chroniques + profil medieval-textual
→ master.json valide, extensions sans iconography
→ valide la généricité (zéro logique Beatus dans le code)
Vérifier pour chaque master.json :
→ ai_raw.json bien séparé
→ processing.provider = "vertex_api_key"
→ schema_version = "1.0"
→ bbox toutes en format [x, y, w, h] avec w > 0 et h > 0
Ajouter tests/test_pipeline.py

Critère de done Session C
3 master.json valides produits (Beatus HR + Beatus BR + Grandes Chroniques).
La basse résolution déclenche bien un score de confidence plus faible.
Les Grandes Chroniques ne contiennent pas de bloc iconography dans extensions.
pytest 100% sur tous les fichiers de test.
ai_raw.json et master.json bien séparés dans data/ pour chaque page.

Critère de fin du Sprint 2

 3 providers connectés et testés
 Syntaxe AQ.Ab documentée dans DECISIONS.md
 Pipeline page unique fonctionnel
 3 master.json valides (Beatus HR + Beatus BR + Grandes Chroniques)
 La basse résolution produit un confidence plus faible que la haute résolution
 Règle de généricité respectée (zéro logique hardcodée Beatus)
 pytest 100%


Ne pas faire dans ce sprint

Aucune API FastAPI
Aucune interface web
Aucun ALTO / METS / IIIF
Aucun traitement en lot
Passes dérivées (traduction, commentaire) : Sprint 3
