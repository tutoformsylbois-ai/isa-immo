from . import bienici, entreparticuliers, iad, lesiteimmo, notaires, pap, paruvendu, safti, seloger, zimo

SOURCES = [lesiteimmo, paruvendu, bienici, seloger, iad, safti, notaires, zimo, entreparticuliers, pap]

# Ce que contient chaque site collecté (affiché sur la page).
CONTENU = {
    "Lesiteimmo": "Agences locales, réseaux (iad, SAFTI…) et notaires",
    "ParuVendu": "Agences et particuliers",
    "Bien'ici": "Agences et mandataires de tous les réseaux",
    "SeLoger": "Agences, réseaux et quelques particuliers",
    "iad": "Mandataires iad (site du réseau)",
    "SAFTI": "Mandataires SAFTI (site du réseau)",
    "Notaires": "Offices notariaux (immobilier.notaires.fr)",
    "Zimo": "Agences et particuliers, dont des particuliers repris de Leboncoin",
    "Entreparticuliers": "Surtout des particuliers, quelques professionnels",
    "PAP": "Particuliers uniquement",
}

# Sites testés mais non collectés, avec la raison (affichés sur la page).
EXCLUS = {
    "Leboncoin": "bloqué par un anti-robot (captcha)",
    "Figaro Immobilier": "accès refusé aux robots (erreur 403)",
    "Ouest-France Immo": "accès refusé aux robots (erreur 403)",
    "Superimmo": "bloqué par un anti-robot",
    "Green-Acres": "pages de résultats interdites aux robots (robots.txt) et captcha",
    "Logic-Immo": "pages de résultats interdites aux robots (robots.txt)",
    "Century 21": "pages de résultats interdites aux robots (robots.txt)",
    "Orpi": "pages de recherche interdites aux robots (robots.txt)",
    "Etreproprio": "pages d'annonces interdites aux robots (robots.txt)",
    "Capifrance, Propriétés-Privées, Square Habitat": "protégés par un anti-robot ; leurs biens paraissent en général sur SeLoger ou Bien'ici",
}
