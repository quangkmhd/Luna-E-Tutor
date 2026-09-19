"""Observable text delivery cues, not a semantic or pronunciation assessment."""
import re


def observe_delivery(context, text: str) -> tuple[int, bool]:
    text = text.casefold()
    counts = [len(re.findall(r'(?<!\w)' + re.escape(word.casefold()) + r'(?!\w)', text))
              for word in context.target_words]
    models = min(counts, default=0) if context.model_repetitions else 0
    invitation = ('?' in text or bool(re.search(r'\b(tell me|your turn|ask me|try saying)\b', text)))
    if context.kind == 'ask_teacher':
        invitation = bool(re.search(r'\bask (me|luna)\b', text))
    return models, invitation
