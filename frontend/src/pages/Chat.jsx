import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import Markdown from "../components/Markdown.jsx";
import { stripCitations } from "../utils.js";

export default function Chat() {
  const { refreshUser } = useAuth();
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setError("");
    setInput("");
    setLoading(true);
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const r = await api("/ai/chat", {
        method: "POST",
        body: { message: text, conversation_id: conversationId },
      });
      setConversationId(r.conversation_id);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: r.answer, sources: r.sources, sufficient: r.sufficient_info, tokens: r.usage.total_tokens },
      ]);
      refreshUser();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    setMessages([]);
    setConversationId(null);
    setError("");
  }

  return (
    <div className="chat">
      <div className="row-between">
        <h2>Chatbot de destinos</h2>
        <button className="btn secondary" onClick={newConversation}>Nueva conversación</button>
      </div>

      <div className="chat-box">
        {messages.length === 0 && (
          <p className="muted center">
            Pregunta sobre los destinos y actividades registrados. Por ejemplo: «¿Qué puedo hacer en el Lago de Atitlán?»
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.role === "user" ? m.content : <Markdown>{stripCitations(m.content)}</Markdown>}
            {m.role === "assistant" &&
              (m.sufficient ? (
                <div className="sources">
                  <span>Fuentes:</span>
                  {m.sources.map((s) => (
                    <span className="chip" key={s.id} title={`similitud ${s.score}`}>{s.title}</span>
                  ))}
                </div>
              ) : (
                <div className="warn-note">Respuesta sin fuentes de la base de datos</div>
              ))}
            {m.role === "assistant" && <small className="muted">{m.tokens} tokens</small>}
          </div>
        ))}
        {loading && <div className="bubble assistant muted">Buscando en la base de conocimiento…</div>}
        <div ref={bottom} />
      </div>

      {error && <div className="error">{error}</div>}
      <form className="chat-input" onSubmit={send}>
        <textarea
          rows={2}
          value={input}
          maxLength={1000}
          placeholder="Escribe tu pregunta (Enter para enviar, Shift+Enter para salto de línea)"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) send(e);
          }}
        />
        <button className="btn" disabled={loading || !input.trim()}>Enviar</button>
      </form>
    </div>
  );
}