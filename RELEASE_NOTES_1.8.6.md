# Olney Engine 1.8.6

- Choix OpenRouter ou OpenAI dans Connexion Emmett.
- Clés distinctes, conservées uniquement en mémoire durant la session.
- Identifiant du modèle libre ; routage OpenRouter automatique par défaut.
- Même contexte calculé, mêmes règles de lecture et même historique.
- Adaptation des réponses et du comptage des jetons OpenRouter.

Validation : 163 tests réussis, dont les contrats OpenRouter et l’isolation des
clés lors d’un changement de service. Aucun appel facturé n’est effectué par
les tests ; une clé utilisateur est nécessaire pour un essai réel.
