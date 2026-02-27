import json
import re

def extract_json(text):
    """
    Extracts JSON from a string, looking for content between triple backticks 
    or the outermost curly braces.
    """
    if not text:
        return None
    
    # Try markdown code block extraction first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding outermost braces
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
            
    return None

def sanitize_evaluation(raw_data):
    """
    Validates and sanitzes the JSON data against the expected schema.
    Returns a structured dictionary with fallback values/messages.
    """
    schema = {
        "origin_analysis": {
            "prediction": str,
            "confidence_score": (float, int),
            "text_artifacts": list,
            "video_artifacts": list,
            "technical_reasoning": str
        },
        "social_performance": {
            "virality_score": (int, float),
            "performance_drivers": list,
            "strategic_reasoning": str
        },
        "distribution_strategy": {
            "target_audiences": list,
            "resonance_factor": str
        },
        "metadata": {
            "analysis_summary": str
        }
    }

    result = {}
    
    if not isinstance(raw_data, dict):
        return None

    for section, fields in schema.items():
        result[section] = {}
        raw_section = raw_data.get(section, {})
        
        # Ensure section is a dict even if LLM messed up
        if not isinstance(raw_section, dict):
            raw_section = {"error_val": raw_section}

        for field, expected_type in fields.items():
            val = raw_section.get(field)
            
            if val is None:
                result[section][field] = "[Missing]"
            elif isinstance(val, expected_type):
                result[section][field] = val
            else:
                # Incorrect data type - coerce to string as requested
                result[section][field] = str(val)
                
    return result
