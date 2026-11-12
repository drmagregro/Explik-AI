# Explik-AI

## Mémoire de la conversation

Le modèle n'a aucune mémoire : à chaque appel, on lui renvoie le prompt système (lu depuis `prompts/system.md`) suivi de l'historique. C'est ce qui lui permet de se souvenir, par exemple, d'un prénom donné plus tôt.

**Stratégie retenue : garder les N derniers échanges** (`MAX_ECHANGES_HISTORIQUE = 10` dans `config.py`, soit 20 messages). L'historique complet reste affiché dans l'interface, mais seule cette fenêtre est envoyée au modèle (`ServiceLLM.preparer_messages`).

Pourquoi :
- **Coût et quota** : chaque token envoyé est facturé et compte dans les limites du palier gratuit de Groq. Sans plafond, chaque message coûterait plus cher que le précédent.
- **Simplicité et fiabilité** : une fenêtre glissante est prévisible et sans appel supplémentaire. Résumer les anciens échanges demanderait un second appel au modèle et risquerait de perdre ou déformer des détails.
- **Suffisant pour une séance de révision** : 10 échanges couvrent le contexte utile d'une discussion.

Limite : au-delà de 10 échanges, les plus anciens sont oubliés (un prénom donné au tout début peut disparaître). Pour une mémoire plus longue, on pourrait résumer les anciens échanges dans un message.

**Si l'historique dépassait la fenêtre de contexte du modèle**, l'API renverrait une erreur (contexte trop long) ou tronquerait l'entrée, et le modèle perdrait le début de la conversation sans prévenir. La fenêtre glissante évite ce cas, et `MAX_TOKENS` plafonne aussi la longueur des réponses.