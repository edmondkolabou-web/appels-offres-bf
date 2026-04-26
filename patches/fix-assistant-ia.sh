#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# NetSync Gov — Patch #7 : Assistant IA complet
# Date : 26 avril 2026
# Usage : cd ~/appels-offres-bf && bash patches/fix-assistant-ia.sh
# ══════════════════════════════════════════════════════════════════════════════

set -e
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NetSync Gov — Patch #7 : Assistant IA                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# 1. Backend : Endpoint /api/v1/assistant/chat
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [1/5] Création backend assistant IA..."

mkdir -p backend/modules/assistant

cat > backend/modules/assistant/__init__.py << 'EOF'
EOF

cat > backend/modules/assistant/backend.py << 'PYEOF'
"""
NetSync Gov — Assistant IA
Endpoint proxy vers Claude API avec contexte AOs BF.
3 modes : questions AO, analyse AO, aide rédaction.
"""
import logging
import os
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.models import Abonne
from backend.security import get_current_abonne

logger = logging.getLogger("netsync.assistant")

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant IA"])


class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    mode: str = "general"  # general, analyse, redaction
    ao_id: Optional[str] = None
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    mode: str
    tokens_used: int = 0


def _get_ao_context(ao_id: str, db: Session) -> str:
    """Récupère le contexte d'un AO pour enrichir le prompt."""
    ao = db.execute(
        text("""
            SELECT titre, reference, autorite_contractante, secteur,
                   type_procedure, statut, date_publication, date_cloture,
                   montant_estime, description, source
            FROM appels_offres WHERE id = :id
        """),
        {"id": ao_id}
    ).fetchone()
    if not ao:
        return ""
    
    ctx = f"""
## Appel d'offres sélectionné
- **Titre** : {ao.titre}
- **Référence** : {ao.reference or 'Non précisée'}
- **Autorité contractante** : {ao.autorite_contractante or 'Non précisée'}
- **Secteur** : {ao.secteur or 'Non précisé'}
- **Type de procédure** : {ao.type_procedure or 'Non précisé'}
- **Statut** : {ao.statut}
- **Date publication** : {ao.date_publication}
- **Date clôture** : {ao.date_cloture or 'Non précisée'}
- **Montant estimé** : {f'{ao.montant_estime:,} FCFA' if ao.montant_estime else 'Non précisé'}
- **Source** : {ao.source}
- **Description** : {ao.description or 'Voir le dossier officiel'}
"""
    return ctx


def _get_stats_context(db: Session) -> str:
    """Récupère des stats générales pour le contexte."""
    stats = db.execute(text("""
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE statut = 'ouvert') AS ouverts,
            COUNT(*) FILTER (WHERE date_publication >= CURRENT_DATE - INTERVAL '30 days') AS ce_mois
        FROM appels_offres
    """)).fetchone()
    return f"Base NetSync Gov : {stats.total} AOs indexés, {stats.ouverts} ouverts, {stats.ce_mois} publiés ce mois."


SYSTEM_PROMPT = """Tu es l'Assistant IA de NetSync Gov, la plateforme de veille des appels d'offres publics du Burkina Faso.

## Ton rôle
Tu aides les PME, consultants et bureaux d'études burkinabè à :
1. Comprendre les appels d'offres (procédures, documents requis, délais)
2. Analyser un AO spécifique (pertinence, risques, recommandations)
3. Rédiger des documents (offre technique, lettre de soumission, note méthodologique)

## Ton expertise
- Marchés publics du Burkina Faso (Code des marchés publics, DGCMEF, ARCOP)
- Procédures : AO ouvert, AO restreint, demande de prix (DPX), AMI, RFP
- Pièces administratives : ASF (DGI), CNSS, AJE, RCCM, IFU
- Plateforme SECOP pour les attestations en ligne
- Sources : Quotidien des Marchés Publics DGCMEF, CCI-BF, UNDP, Banque Mondiale

## Règles
- Réponds toujours en français
- Sois précis, concret et actionnable
- Cite les articles du Code des marchés publics quand pertinent
- Si tu ne sais pas, dis-le honnêtement
- Propose toujours une prochaine action concrète
- Utilise le formatage Markdown (gras, listes, titres)
- Reste concis — 200-400 mots maximum sauf pour la rédaction
"""

MODE_PROMPTS = {
    "general": "L'utilisateur pose une question générale sur les marchés publics au Burkina Faso ou sur la plateforme NetSync Gov.",
    "analyse": """L'utilisateur demande une analyse d'un appel d'offres spécifique. Tu dois :
1. Résumer l'AO en 3-4 phrases
2. Évaluer la pertinence (secteur, montant, complexité)
3. Identifier les risques et les points d'attention
4. Lister les pièces administratives requises
5. Recommander une stratégie go/no-go
6. Estimer le temps de préparation du dossier""",
    "redaction": """L'utilisateur demande de l'aide pour rédiger un document de soumission. Tu dois :
1. Demander les informations manquantes si nécessaire
2. Produire un document professionnel et structuré
3. Adapter au contexte burkinabè (formulations, références réglementaires)
4. Inclure des [À COMPLÉTER] pour les données spécifiques
5. Suivre la structure standard des offres BF"""
}


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """
    Endpoint principal de l'assistant IA.
    Utilise Claude API avec contexte AOs BF.
    Réservé aux abonnés Pro.
    """
    if not abonne.est_pro:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="L'assistant IA est réservé aux abonnés Pro. Passez au plan Pro pour y accéder."
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service IA temporairement indisponible. Veuillez réessayer plus tard."
        )

    # Construire le contexte
    context_parts = [SYSTEM_PROMPT]
    context_parts.append(f"\n## Mode actif : {body.mode}")
    context_parts.append(MODE_PROMPTS.get(body.mode, MODE_PROMPTS["general"]))
    context_parts.append(f"\n## Contexte\n{_get_stats_context(db)}")
    context_parts.append(f"Date du jour : {date.today().isoformat()}")

    if body.ao_id:
        ao_ctx = _get_ao_context(body.ao_id, db)
        if ao_ctx:
            context_parts.append(ao_ctx)

    # Abonné info
    context_parts.append(f"\n## Utilisateur\nNom : {abonne.prenom} {abonne.nom}\nEntreprise : {abonne.entreprise or 'Non précisée'}\nPlan : {abonne.plan}")

    system_prompt = "\n".join(context_parts)

    # Construire les messages
    messages = []
    for msg in body.history[-10:]:  # Garder les 10 derniers messages
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": body.message})

    # Appel Claude API
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        
        reply = response.content[0].text
        tokens = response.usage.output_tokens

        logger.info(f"Assistant IA: {abonne.email} mode={body.mode} tokens={tokens}")

        return ChatResponse(
            reply=reply,
            mode=body.mode,
            tokens_used=tokens,
        )

    except Exception as e:
        logger.error(f"Erreur Claude API: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erreur de communication avec le service IA. Veuillez réessayer."
        )


@router.get("/suggestions")
def get_suggestions(
    abonne: Abonne = Depends(get_current_abonne),
    db: Session = Depends(get_db),
):
    """Retourne des suggestions de questions contextuelles."""
    suggestions = [
        {"icon": "🔍", "text": "Quels AOs correspondent à mon profil ?", "mode": "general"},
        {"icon": "📋", "text": "Quelles pièces administratives dois-je préparer pour un AO ouvert ?", "mode": "general"},
        {"icon": "⏰", "text": "Quels sont les délais typiques pour répondre à un AO au Burkina ?", "mode": "general"},
        {"icon": "💰", "text": "Comment estimer le montant de mon offre financière ?", "mode": "general"},
        {"icon": "📝", "text": "Aide-moi à rédiger une offre technique", "mode": "redaction"},
        {"icon": "🏛️", "text": "Explique-moi la procédure d'AO restreint au Burkina Faso", "mode": "general"},
    ]

    # Ajouter des suggestions contextuelles basées sur les AOs urgents
    urgents = db.execute(text("""
        SELECT id, titre, secteur FROM appels_offres
        WHERE statut = 'ouvert' AND date_cloture <= CURRENT_DATE + INTERVAL '7 days'
        AND date_cloture >= CURRENT_DATE
        ORDER BY date_cloture ASC LIMIT 2
    """)).fetchall()

    for ao in urgents:
        suggestions.insert(0, {
            "icon": "⚡",
            "text": f"Analyse cet AO urgent : {ao.titre[:60]}...",
            "mode": "analyse",
            "ao_id": str(ao.id),
        })

    return {"suggestions": suggestions[:8]}
PYEOF

echo "   ✅ Backend assistant IA créé (chat + suggestions)"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Frontend : Page AssistantView.vue
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [2/5] Création page AssistantView.vue..."

cat > frontend/src/views/AssistantView.vue << 'VUEEOF'
<template>
  <div class="assistant-page">
    <!-- Header -->
    <div class="assistant-header">
      <div>
        <h1 class="page-title">Assistant IA</h1>
        <p class="page-sub">Posez vos questions sur les marchés publics du Burkina Faso</p>
      </div>
      <div class="mode-selector">
        <button v-for="m in modes" :key="m.id" :class="['mode-btn', { active: mode === m.id }]" @click="mode = m.id">
          <span class="mode-icon">{{ m.icon }}</span>
          <span>{{ m.label }}</span>
        </button>
      </div>
    </div>

    <!-- AO Context selector -->
    <div v-if="mode === 'analyse'" class="ao-selector card">
      <label class="ao-selector-label">Sélectionner un AO à analyser :</label>
      <select v-model="selectedAoId" class="ao-select">
        <option value="">Choisir un appel d'offres...</option>
        <option v-for="ao in recentAOs" :key="ao.id" :value="ao.id">
          {{ ao.titre?.slice(0, 80) }} — {{ ao.secteur }}
        </option>
      </select>
    </div>

    <!-- Chat area -->
    <div class="chat-container card">
      <!-- Messages -->
      <div class="chat-messages" ref="messagesContainer">
        <!-- Welcome message -->
        <div v-if="!messages.length" class="welcome-area">
          <div class="welcome-icon">🤖</div>
          <h2 class="welcome-title">Bienvenue sur l'Assistant IA NetSync Gov</h2>
          <p class="welcome-desc">
            Je suis votre expert en marchés publics du Burkina Faso. Je peux vous aider à comprendre les AOs,
            analyser leur pertinence, ou rédiger vos documents de soumission.
          </p>

          <!-- Suggestions -->
          <div class="suggestions-grid">
            <button v-for="s in suggestions" :key="s.text" class="suggestion-card" @click="sendSuggestion(s)">
              <span class="suggestion-icon">{{ s.icon }}</span>
              <span class="suggestion-text">{{ s.text }}</span>
            </button>
          </div>
        </div>

        <!-- Message bubbles -->
        <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
          <div class="message-avatar" v-if="msg.role === 'assistant'">🤖</div>
          <div class="message-bubble">
            <div v-if="msg.role === 'assistant'" class="message-content" v-html="renderMarkdown(msg.content)"></div>
            <div v-else class="message-content">{{ msg.content }}</div>
            <div class="message-meta">
              <span v-if="msg.tokens" class="message-tokens">{{ msg.tokens }} tokens</span>
              <span class="message-time">{{ msg.time }}</span>
            </div>
          </div>
          <div class="message-avatar user-avatar" v-if="msg.role === 'user'">{{ initiales }}</div>
        </div>

        <!-- Typing indicator -->
        <div v-if="loading" class="message assistant">
          <div class="message-avatar">🤖</div>
          <div class="message-bubble typing">
            <div class="typing-dots">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <div class="chat-input-wrap">
          <textarea
            ref="inputRef"
            v-model="input"
            @keydown.enter.exact.prevent="sendMessage"
            :placeholder="inputPlaceholder"
            :disabled="loading"
            rows="1"
            class="chat-input"
          ></textarea>
          <button class="send-btn" @click="sendMessage" :disabled="!input.trim() || loading">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <p class="chat-disclaimer">L'IA peut faire des erreurs. Vérifiez les informations importantes.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import api from '@/api'

const authStore = useAuthStore()
const toast = useToastStore()

const messages = ref([])
const input = ref('')
const loading = ref(false)
const mode = ref('general')
const selectedAoId = ref('')
const suggestions = ref([])
const recentAOs = ref([])
const messagesContainer = ref(null)
const inputRef = ref(null)

const initiales = computed(() => authStore.initiales || '?')

const modes = [
  { id: 'general', icon: '💬', label: 'Questions' },
  { id: 'analyse', icon: '🔍', label: 'Analyse AO' },
  { id: 'redaction', icon: '✍️', label: 'Rédaction' },
]

const inputPlaceholder = computed(() => {
  switch (mode.value) {
    case 'analyse': return 'Posez une question sur cet AO...'
    case 'redaction': return 'Décrivez ce que vous voulez rédiger...'
    default: return 'Posez votre question sur les marchés publics BF...'
  }
})

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^### (.*$)/gm, '<h4>$1</h4>')
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')
    .replace(/^# (.*$)/gm, '<h2>$1</h2>')
    .replace(/^- (.*$)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^(.*)$/, '<p>$1</p>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

function getTime() {
  return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text, time: getTime() })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const { data } = await api.post('/assistant/chat', {
      message: text,
      mode: mode.value,
      ao_id: selectedAoId.value || null,
      history: messages.value.slice(-10).map(m => ({ role: m.role, content: m.content })),
    })

    messages.value.push({
      role: 'assistant',
      content: data.reply,
      time: getTime(),
      tokens: data.tokens_used,
    })
  } catch (err) {
    const detail = err.response?.data?.detail || 'Erreur de communication avec l\'assistant'
    messages.value.push({
      role: 'assistant',
      content: `❌ ${detail}`,
      time: getTime(),
    })
    if (err.response?.status === 402) {
      toast.add('L\'assistant IA est réservé au plan Pro', 'error')
    }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function sendSuggestion(s) {
  if (s.mode) mode.value = s.mode
  if (s.ao_id) selectedAoId.value = s.ao_id
  input.value = s.text
  sendMessage()
}

async function loadSuggestions() {
  try {
    const { data } = await api.get('/assistant/suggestions')
    suggestions.value = data.suggestions || []
  } catch {
    suggestions.value = [
      { icon: '📋', text: 'Quelles pièces pour un AO ouvert ?', mode: 'general' },
      { icon: '⏰', text: 'Quels sont les délais typiques ?', mode: 'general' },
      { icon: '📝', text: 'Aide-moi à rédiger une offre', mode: 'redaction' },
    ]
  }
}

async function loadRecentAOs() {
  try {
    const { data } = await api.get('/aos', { params: { statut: 'ouvert', per_page: 20 } })
    recentAOs.value = data.items || []
  } catch {}
}

watch(mode, () => {
  if (mode.value === 'analyse') loadRecentAOs()
})

onMounted(() => {
  loadSuggestions()
  inputRef.value?.focus()
})
</script>

<style scoped>
.assistant-page { display:flex; flex-direction:column; gap:1rem; height:calc(100vh - 56px - 3rem); }

.assistant-header { display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:1rem; }
.page-title { font-family:var(--font-display); font-size:1.5rem; color:var(--ink); }
.page-sub { font-size:13px; color:var(--muted); margin-top:4px; }

.mode-selector { display:flex; gap:6px; }
.mode-btn { display:flex; align-items:center; gap:5px; padding:7px 14px; border-radius:var(--radius-full); border:1px solid var(--border-md); background:var(--white); color:var(--muted); font-size:12px; font-weight:500; cursor:pointer; transition:all .15s; font-family:inherit; }
.mode-btn:hover { border-color:var(--blue-300); color:var(--ink); }
.mode-btn.active { background:var(--blue-500); color:var(--white); border-color:var(--blue-500); }
.mode-icon { font-size:14px; }

.ao-selector { padding:12px 16px; display:flex; align-items:center; gap:12px; }
.ao-selector-label { font-size:12px; font-weight:500; color:var(--ink); white-space:nowrap; }
.ao-select { flex:1; font-family:inherit; font-size:12px; border:1px solid var(--border-md); border-radius:var(--radius-md); padding:8px 12px; background:var(--white); color:var(--ink); }

.chat-container { flex:1; display:flex; flex-direction:column; overflow:hidden; padding:0; }

.chat-messages { flex:1; overflow-y:auto; padding:1.5rem; display:flex; flex-direction:column; gap:1rem; }

/* Welcome */
.welcome-area { display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:2rem 1rem; flex:1; }
.welcome-icon { font-size:48px; margin-bottom:1rem; }
.welcome-title { font-family:var(--font-display); font-size:1.25rem; color:var(--ink); margin-bottom:.5rem; }
.welcome-desc { font-size:13px; color:var(--muted); max-width:480px; line-height:1.6; margin-bottom:2rem; }

.suggestions-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; max-width:560px; width:100%; }
.suggestion-card { display:flex; align-items:flex-start; gap:8px; padding:12px 14px; border:1px solid var(--border); border-radius:var(--radius-lg); background:var(--white); cursor:pointer; transition:all .15s; text-align:left; font-family:inherit; }
.suggestion-card:hover { border-color:var(--blue-300); background:var(--blue-50); }
.suggestion-icon { font-size:16px; flex-shrink:0; margin-top:1px; }
.suggestion-text { font-size:12px; color:var(--ink-500); line-height:1.4; }

/* Messages */
.message { display:flex; gap:10px; max-width:85%; }
.message.user { margin-left:auto; flex-direction:row-reverse; }
.message-avatar { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; flex-shrink:0; background:var(--blue-50); }
.user-avatar { background:var(--blue-500); color:var(--white); font-size:11px; font-weight:600; }
.message-bubble { padding:12px 16px; border-radius:var(--radius-lg); max-width:100%; }
.message.assistant .message-bubble { background:var(--surface); border:1px solid var(--border); border-top-left-radius:4px; }
.message.user .message-bubble { background:var(--blue-500); color:var(--white); border-top-right-radius:4px; }
.message-content { font-size:13px; line-height:1.6; }
.message-content :deep(h2) { font-size:15px; font-weight:600; margin:12px 0 6px; }
.message-content :deep(h3) { font-size:14px; font-weight:600; margin:10px 0 4px; }
.message-content :deep(h4) { font-size:13px; font-weight:600; margin:8px 0 4px; }
.message-content :deep(ul) { padding-left:16px; margin:6px 0; }
.message-content :deep(li) { margin-bottom:3px; }
.message-content :deep(code) { background:rgba(0,0,0,.06); padding:1px 5px; border-radius:3px; font-family:var(--font-mono); font-size:12px; }
.message-content :deep(strong) { font-weight:600; }
.message-content :deep(p) { margin-bottom:8px; }
.message-content :deep(p:last-child) { margin-bottom:0; }
.message-meta { display:flex; gap:8px; margin-top:6px; font-size:10px; color:var(--muted); }
.message.user .message-meta { color:rgba(255,255,255,.5); justify-content:flex-end; }
.message-tokens { font-family:var(--font-mono); }

/* Typing indicator */
.typing { padding:16px 20px; }
.typing-dots { display:flex; gap:4px; }
.typing-dots span { width:6px; height:6px; border-radius:50%; background:var(--muted); animation:typing-bounce .6s infinite alternate; }
.typing-dots span:nth-child(2) { animation-delay:.15s; }
.typing-dots span:nth-child(3) { animation-delay:.3s; }
@keyframes typing-bounce { to { opacity:.3; transform:translateY(-4px); } }

/* Input */
.chat-input-area { padding:1rem 1.5rem; border-top:1px solid var(--border); background:var(--white); }
.chat-input-wrap { display:flex; align-items:flex-end; gap:8px; background:var(--surface); border:1px solid var(--border-md); border-radius:var(--radius-lg); padding:8px 8px 8px 14px; transition:border-color .15s; }
.chat-input-wrap:focus-within { border-color:var(--blue-400); }
.chat-input { flex:1; border:none; background:none; font-family:inherit; font-size:14px; color:var(--ink); resize:none; outline:none; max-height:120px; line-height:1.5; }
.chat-input::placeholder { color:var(--muted); }
.send-btn { width:36px; height:36px; border-radius:var(--radius-md); background:var(--blue-500); color:var(--white); border:none; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all .15s; flex-shrink:0; }
.send-btn:hover { background:var(--blue-600); }
.send-btn:disabled { background:var(--border-md); cursor:not-allowed; }
.chat-disclaimer { font-size:10px; color:var(--muted); text-align:center; margin-top:8px; }

@media (max-width:768px) {
  .suggestions-grid { grid-template-columns:1fr; }
  .mode-selector { flex-wrap:wrap; }
  .message { max-width:95%; }
  .ao-selector { flex-direction:column; align-items:stretch; }
}
</style>
VUEEOF

echo "   ✅ Page AssistantView.vue créée"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Enregistrer le router dans main.py
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [3/5] Enregistrement router assistant dans main.py..."

python3 << 'PYFIX3'
with open("backend/main.py", "r") as f:
    content = f.read()

if "assistant" not in content:
    # Ajouter l'import
    content = content.replace(
        "from backend.modules.transparence.backend import router as transparence_router",
        "from backend.modules.transparence.backend import router as transparence_router\nfrom backend.modules.assistant.backend import router as assistant_router"
    )
    # Ajouter l'include_router
    content = content.replace(
        "app.include_router(transparence_router)",
        "app.include_router(transparence_router)\napp.include_router(assistant_router)  # /api/v1/assistant"
    )
    with open("backend/main.py", "w") as f:
        f.write(content)
    print("   ✅ Router assistant enregistré dans main.py")
else:
    print("   ℹ️  Router assistant déjà présent")
PYFIX3


# ──────────────────────────────────────────────────────────────────────────────
# 4. Ajouter la route frontend + sidebar
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [4/5] Ajout route /assistant + sidebar..."

python3 << 'PYFIX4'
# Router
with open("frontend/src/router/index.js", "r") as f:
    content = f.read()

if "Assistant" not in content:
    content = content.replace(
        "{ path: 'institutions',     name: 'Institutions',  component: () => import('@/views/InstitutionsView.vue') },",
        "{ path: 'institutions',     name: 'Institutions',  component: () => import('@/views/InstitutionsView.vue') },\n      { path: 'assistant',        name: 'Assistant',     component: () => import('@/views/AssistantView.vue') },"
    )
    # Ajouter le titre
    content = content.replace(
        "Institutions: 'Mon institution'",
        "Institutions: 'Mon institution',\n                 Assistant: 'Assistant IA'"
    )
    with open("frontend/src/router/index.js", "w") as f:
        f.write(content)
    print("   ✅ Route /assistant ajoutée")

# Sidebar
with open("frontend/src/components/layout/AppLayout.vue", "r") as f:
    content = f.read()

if "Assistant" not in content:
    # Ajouter l'icône
    content = content.replace(
        "const IconBuilding",
        "const IconBot      = { template: \`<svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"3\" y=\"11\" width=\"18\" height=\"10\" rx=\"2\"/><circle cx=\"12\" cy=\"5\" r=\"4\"/><line x1=\"8\" y1=\"16\" x2=\"8\" y2=\"16.01\"/><line x1=\"16\" y1=\"16\" x2=\"16\" y2=\"16.01\"/></svg>\` }\nconst IconBuilding"
    )
    # Ajouter dans navItems
    content = content.replace(
        "{ to: '/institutions', label: 'Mon institution', icon: IconBuilding },",
        "{ to: '/institutions', label: 'Mon institution', icon: IconBuilding },\n  { to: '/assistant',    label: 'Assistant IA',    icon: IconBot },"
    )
    with open("frontend/src/components/layout/AppLayout.vue", "w") as f:
        f.write(content)
    print("   ✅ Assistant IA ajouté à la sidebar")
PYFIX4


# ──────────────────────────────────────────────────────────────────────────────
# 5. Ajouter l'API client dans api.js
# ──────────────────────────────────────────────────────────────────────────────
echo "🔧 [5/5] Ajout API client assistant..."

python3 << 'PYFIX5'
with open("frontend/src/api.js", "r") as f:
    content = f.read()

if "assistantApi" not in content:
    new_api = """
export const assistantApi = {
  chat:        (data) => api.post('/assistant/chat', data),
  suggestions: ()     => api.get('/assistant/suggestions'),
}
"""
    content = content.replace("export default api", new_api + "\nexport default api")
    with open("frontend/src/api.js", "w") as f:
        f.write(content)
    print("   ✅ API client assistant ajouté")
else:
    print("   ℹ️  API client déjà présent")
PYFIX5


# ──────────────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "✅ Patch #7 terminé — Assistant IA complet :"
echo ""
echo "  BACKEND  ✅ /api/v1/assistant/chat (proxy Claude API)"
echo "           ✅ /api/v1/assistant/suggestions (contextuel)"
echo "  FRONTEND ✅ Page /assistant (chat, suggestions, modes)"
echo "  SIDEBAR  ✅ Lien Assistant IA avec icône robot"
echo "  MODES    ✅ 3 modes : Questions / Analyse AO / Rédaction"
echo ""
echo "Fonctionnalités :"
echo "  • Chat en temps réel avec Claude Sonnet"
echo "  • Contexte automatique (stats BDD, AO sélectionné, profil user)"
echo "  • Suggestions contextuelles (AOs urgents inclus)"
echo "  • Sélecteur d'AO pour le mode analyse"
echo "  • Rendu Markdown (titres, listes, code, gras)"
echo "  • Historique conversation (10 derniers messages)"
echo "  • Réservé aux abonnés Pro (402 si gratuit)"
echo ""
echo "⚠️  Nécessite ANTHROPIC_API_KEY dans le .env"
echo ""
echo "  git add -A"
echo "  git commit -m 'feat: assistant IA complet — chat Claude, 3 modes, suggestions (patch #7)'"
echo "  git push origin main"
echo "══════════════════════════════════════════════════════════════"
