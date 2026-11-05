export const SERVICES = [
  { code: "rag_chat", label: "Chatbot de destinos" },
  { code: "itinerary_planner", label: "Planificador de itinerarios" },
  { code: "plan_adjuster", label: "Ajustador de plan" },
];

export const SHORT = {
  rag_chat: "Chatbot",
  itinerary_planner: "Planificador",
  plan_adjuster: "Ajustador",
};

// Quita las citas [1], [2] del texto (las fuentes se muestran aparte)
export const stripCitations = (t) => (t || "").replace(/\s*\[\d+\]/g, "");

export const fmtNum = (n) => Number(n || 0).toLocaleString("es-GT");

export const fmtDate = (iso) =>
  new Date(iso).toLocaleString("es-GT", { timeZone: "America/Guatemala" });