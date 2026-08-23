import React, { useState, useEffect, useRef } from "react";

export default function ChatWidget({ apiUrl = "http://localhost:8000" }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Generate unique session ID on mount
    const id = "sess_" + Math.random().toString(36).substr(2, 9);
    setSessionId(id);
    setMessages([
      {
        role: "assistant",
        content: "Hi! I'm here to help you find the right resume package. What kind of roles or career stage are you targeting?",
      },
    ]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async (textToSend) => {
    const text = textToSend || input.trim();
    if (!text || loading) return;

    setInput("");
    const newHistory = [...messages, { role: "user", content: text }];
    setMessages(newHistory);
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);

      if (data.done && data.recommendation) {
        setRecommendation(data.recommendation);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I had trouble connecting to the service. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 1000, fontFamily: "sans-serif" }}>
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            background: "#0d9488",
            color: "#fff",
            border: "none",
            borderRadius: "50%",
            width: 60,
            height: 60,
            fontSize: 26,
            cursor: "pointer",
            boxShadow: "0 4px 14px rgba(0,0,0,0.2)",
          }}
        >
          💼
        </button>
      )}

      {isOpen && (
        <div
          style={{
            width: 380,
            height: 520,
            background: "#fff",
            borderRadius: 12,
            boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            border: "1px solid #e5e7eb",
          }}
        >
          {/* Header */}
          <div style={{ background: "#0d9488", color: "#fff", padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Resume Advisor</div>
              <div style={{ fontSize: 12, opacity: 0.9 }}>Find your ideal package</div>
            </div>
            <button onClick={() => setIsOpen(false)} style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer" }}>✕</button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {messages.map((m, idx) => (
              <div key={idx} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%" }}>
                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: 12,
                    fontSize: 14,
                    lineHeight: 1.5,
                    background: m.role === "user" ? "#0d9488" : "#f3f4f6",
                    color: m.role === "user" ? "#fff" : "#1f2937",
                  }}
                >
                  {m.content}
                </div>
              </div>
            ))}

            {loading && <div style={{ fontSize: 13, color: "#6b7280", fontStyle: "italic" }}>Advisor is typing...</div>}

            {/* Recommendation Result Card */}
            {recommendation && (
              <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 10, padding: 14, marginTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#166534", textTransform: "uppercase" }}>Recommended Package</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#14532d", margin: "4px 0" }}>
                  {recommendation.name} — ${recommendation.price}
                </div>
                <div style={{ fontSize: 13, color: "#374151", marginBottom: 8 }}>{recommendation.summary}</div>
                <div style={{ fontSize: 12, color: "#15803d", background: "#dcfce7", padding: "6px 8px", borderRadius: 6 }}>
                  💡 {recommendation.reason}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div style={{ padding: "12px", borderTop: "1px solid #e5e7eb", display: "flex", gap: 8 }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type your answer..."
              style={{ flex: 1, padding: "8px 12px", border: "1px solid #d1d5db", borderRadius: 20, outline: "none", fontSize: 14 }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading}
              style={{ background: "#0d9488", color: "#fff", border: "none", borderRadius: "50%", width: 36, height: 36, cursor: "pointer" }}
            >
              ➔
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
