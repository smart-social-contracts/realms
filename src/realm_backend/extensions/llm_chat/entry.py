from kybra import Record, ic, text

class LLMChatResponse(Record):
    response: text

def get_config() -> LLMChatResponse:
    """Get configuration for the LLM chat extension.
    
    Returns:
        LLMChatResponse: A simple acknowledgment
    """
    return LLMChatResponse(response="LLM Chat extension is ready") 