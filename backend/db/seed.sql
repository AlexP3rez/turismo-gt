-- Servicios de IA
INSERT INTO ai_services (code, name, description) VALUES
('rag_chat',          'Chatbot de destinos',       'Responde consultas sobre los destinos y actividades registrados (RAG).'),
('itinerary_planner', 'Planificador de itinerarios','Busca lugares, consulta clima y distancias y arma un itinerario.'),
('plan_adjuster',     'Ajustador de plan',          'Ajusta un itinerario ante cambios de presupuesto o clima buscando alternativas.');

-- Destinos
INSERT INTO destinations (name, department, category, description) VALUES
('Quetzaltenango (Xela)', 'Quetzaltenango', 'ciudad',
 'Segunda ciudad más grande de Guatemala, ubicada en las tierras altas a unos 2,330 m de altitud. Su centro histórico gira en torno al Parque Central, con arquitectura neoclásica. Es base para visitar aguas termales, volcanes y pueblos indígenas cercanos. Clima fresco todo el año.'),
('Lago de Atitlán', 'Sololá', 'naturaleza',
 'Lago de origen volcánico rodeado de tres volcanes y pueblos mayas a su orilla, como Panajachel, San Juan La Laguna y San Pedro La Laguna. Se recorre en lancha. Ofrece caminatas, kayak, cooperativas de tejidos y miradores.'),
('Antigua Guatemala', 'Sacatepéquez', 'ciudad',
 'Ciudad colonial declarada Patrimonio de la Humanidad por la UNESCO. Destaca por sus calles empedradas, ruinas de iglesias y conventos, el Arco de Santa Catalina y vistas a los volcanes de Agua, Fuego y Acatenango. Tiene gran oferta gastronómica y de café.'),
('Parque Nacional Tikal', 'Petén', 'arqueología',
 'Antigua ciudad maya en medio de la selva del Petén, con templos que sobresalen del dosel. La Gran Plaza y el Templo IV son los puntos más visitados. Se recomienda ir temprano para ver el amanecer y la fauna. Clima cálido y húmedo.'),
('Semuc Champey', 'Alta Verapaz', 'naturaleza',
 'Monumento natural con pozas de agua color turquesa formadas sobre un puente de piedra caliza sobre el río Cahabón. Cerca están las cuevas de K''anba y el pueblo de Lanquín. El acceso es por caminos largos y accidentados. Zona lluviosa.'),
('Chichicastenango', 'Quiché', 'cultura',
 'Pueblo de las tierras altas conocido por su mercado tradicional de jueves y domingo, y por la iglesia de Santo Tomás, donde se mezclan rituales católicos y mayas. Ideal para artesanías, textiles y cultura k''iche''.'),
('Volcán de Pacaya', 'Escuintla', 'aventura',
 'Volcán activo cercano a la capital con senderos guiados de dificultad media. Permite caminar sobre campos de lava solidificada y, según la actividad, ver lava. Se recomienda calzado cerrado, ropa abrigada y salir por la tarde.'),
('Río Dulce y Livingston', 'Izabal', 'naturaleza',
 'Zona de río, lago y costa caribeña. El Castillo de San Felipe protege la entrada al lago de Izabal y Livingston es un pueblo garífuna accesible solo por lancha. Clima tropical, con gastronomía como el tapado.');

-- Actividades (costos en quetzales y coordenadas APROXIMADAS: verifícalos y ajústalos)
INSERT INTO activities (destination_id, name, description, category, est_cost_gtq, duration_hours, latitude, longitude) VALUES
(1, 'Recorrido por el Parque Central', 'Caminata por el centro histórico, catedral y edificios neoclásicos.', 'cultura', 0, 2, 14.8347, -91.5181),
(1, 'Aguas termales Fuentes Georginas', 'Pozas termales entre bosque nuboso en las faldas del volcán Zunil.', 'naturaleza', 60, 4, 14.7261, -91.4772),
(1, 'Mercado y gastronomía local', 'Degustación de platillos típicos en el mercado de la ciudad.', 'gastronomía', 50, 2, 14.8450, -91.5200),
(2, 'Paseo en lancha entre pueblos', 'Recorrido por Panajachel, San Juan y San Pedro La Laguna.', 'naturaleza', 100, 5, 14.7420, -91.1590),
(2, 'Cooperativa de tejidos en San Juan', 'Demostración de tejido y tinte natural con mujeres artesanas.', 'cultura', 30, 2, 14.6970, -91.2740),
(2, 'Kayak al amanecer', 'Remo sobre el lago en la mañana, con aguas calmas.', 'aventura', 120, 3, 14.6910, -91.2690),
(3, 'Arco de Santa Catalina y centro histórico', 'Recorrido a pie por las calles coloniales y ruinas.', 'cultura', 0, 3, 14.5586, -90.7345),
(3, 'Mirador Cerro de la Cruz', 'Vista panorámica de la ciudad y el volcán de Agua.', 'naturaleza', 0, 1.5, 14.5666, -90.7314),
(3, 'Tour de café', 'Visita a una finca con proceso y cata de café.', 'gastronomía', 150, 3, 14.5600, -90.7340),
(4, 'Visita guiada a la Gran Plaza', 'Recorrido por los templos I y II y acrópolis.', 'arqueología', 200, 4, 17.2220, -89.6237),
(4, 'Amanecer en el Templo IV', 'Ascenso al templo más alto para ver el amanecer sobre la selva.', 'arqueología', 250, 4, 17.2233, -89.6137),
(5, 'Pozas de Semuc Champey', 'Baño en las pozas y caminata al mirador.', 'naturaleza', 100, 5, 15.7850, -89.9580),
(5, 'Cuevas de K''anba', 'Recorrido con velas por una cueva y el río.', 'aventura', 90, 2, 15.7870, -89.9560),
(6, 'Mercado de Chichicastenango', 'Compra de artesanías y textiles (jueves y domingo).', 'cultura', 0, 3, 14.9420, -91.1110),
(7, 'Ascenso guiado al Pacaya', 'Caminata de dificultad media sobre campos de lava.', 'aventura', 100, 4, 14.3810, -90.6010),
(8, 'Castillo de San Felipe', 'Fortaleza colonial a la orilla del lago de Izabal.', 'cultura', 40, 2, 15.7793, -89.0000),
(8, 'Lancha a Livingston', 'Viaje por el río Dulce hasta la costa caribeña.', 'naturaleza', 150, 5, 15.8280, -88.7510);