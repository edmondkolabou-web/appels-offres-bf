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
