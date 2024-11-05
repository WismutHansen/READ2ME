from langchain_core.prompts import PromptTemplate

pod = PromptTemplate.from_template(
    """
    Using the text highlighted between ###, please generate a detailed and intriguing podcast transcription between two speakers,
    a man and a woman. The conversation should flow naturally and explore the content of the seed text in an engaging way. 
    Include filler words like "um," "you know," and "like" to make it sound as human as possible.
    Speakers should be identifiable by their names at the beginning of their lines (e.g., "speaker1:" and "speaker2:").
    Do not include any additional annotations such as stage directions or sound effects e.g. (laughing).
    The transcription should read like a real conversation between two people discussing the topic.
    No names are used in the dialogue.
    ###
    {text}
    ###
    Provide your response in the following JSON format:
    {format_instructions}
    """
)

title_prompt = PromptTemplate.from_template(
    """
    Create a 3-word title for the text highlighted between ###. Output only the 3-word title and nothing else!
    ###
    {text}
    ###
    """
)

story_mode = PromptTemplate.from_template(
    """
    turn the text highlighted between ### into an exciting story for children!
    ###
    {text}
    ###
    """
)

story_mode_with_language = PromptTemplate.from_template(
    """
    turn the text highlighted between ### into an exciting story for children in {language}!
    ###
    {text}
    ###
    """
)

summ_prompt = PromptTemplate.from_template(
    """
    Return a concise summary for the text highlighted between ###, without referencing the text 
    or mentioning 'in the text' or similar phrases. Keep the tone and perspective of the original text.
    ###
    {text}
    ###
    """
)