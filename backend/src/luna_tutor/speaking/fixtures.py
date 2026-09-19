from luna_tutor.speaking.models import Evidence, Reply, SuggestedWord, Suggestions, WordUse


class FixtureSpeakingModels:
    async def suggest(self, topic):
        return Suggestions(topic=topic, words=(
            SuggestedWord(word='explore', meaning_vi='khám phá', example='I want to explore it.'),
            SuggestedWord(word='exciting', meaning_vi='thú vị', example='It is exciting!'),
        ))

    async def opening(self, state):
        return Reply(text=f"Let’s talk about {state.config.topic}! What do you like about it?")

    async def evaluate(self, state, turn):
        lowered = turn.text.casefold()
        if 'stop' in lowered or 'dừng' in lowered:
            return Evidence(kind='finish')
        if 'help' in lowered or 'không biết' in lowered:
            return Evidence(kind='help', difficulty=True)
        uses = tuple(WordUse(word=word, quote=word, independent=True)
                     for word in state.config.words if word in lowered)
        return Evidence(kind='answer', independent=bool(turn.text.split()), word_uses=uses)

    async def reply(self, state, turn, evidence, decision):
        if decision.action == 'finish':
            return Reply(text='You did well sharing your ideas today. See you next time!')
        if decision.action == 'offer_choices':
            return Reply(text='You can choose: is it fun or exciting?', support_kind='choices')
        return Reply(text='That is interesting! Can you tell me one reason?')
