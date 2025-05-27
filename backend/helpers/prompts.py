import sys
from yachalk import chalk
sys.path.append("..")

import json
import ollama.client as client


def extractConcepts(prompt: str, metadata={}, model="mistral-openorca:latest"):
    SYS_PROMPT = (
        "Your task is to extract key concepts, entities, and their explicit relationships mentioned in the given context. "

        "Focus on extracting relationships that connect concepts to form a comprehensive and detailed knowledge graph. "
        "Extract as many meaningful concepts and relationships as possible, including hierarchical relationships, causal connections, and temporal sequences. "
        "Categorize the concepts in one of the following categories: [event, concept, place, object, document, organisation, condition, process, attribute, role, system, misc]. "
        "For each concept, provide detailed properties and multiple relationships to other concepts. "
        "Format your output as a list of JSON with the following format: "
        "[\n"
        "   {\n"
        '       "entity": "The Concept (be as specific and detailed as possible)",\n'
        '       "category": "The Type of Concept",\n'
        '       "description": "A detailed description of the concept",\n'
        '       "relationships": [ \n'
        '           { \n'


        '               "type": "The type of relationship (e.g., \'is a\', \'has part\', \'causes\', \'precedes\', \'influences\', \'depends on\', \'related to\')", \n'
        '               "target_entity": "The concept related to the main entity",\n'
        '               "description": "Detailed explanation of how these concepts are related"\n'
        '           }\n'
        '       ],\n'
        '       "properties": [ \n'
        '           { \n'
        '               "name": "Property name", \n'

        '               "value": "Property value",\n'
        '               "source": "Source of this property (if applicable)"\n'
        '           }\n'
        '       ],\n'
        '       "sub_concepts": [\n'
        '           {\n'
        '               "entity": "Related sub-concept",\n'
        '               "relationship": "How it relates to the parent concept"\n'
        '           }\n'
        '       ]\n'


        "   }\n"
        "]\n"

        "Ensure to extract a comprehensive set of concepts, their properties, and interconnected relationships to create a rich knowledge graph."
    )    
    response, _ = client.generate(model_name=model, system=SYS_PROMPT, prompt=prompt)
    try:
        result = json.loads(response)
        result = [dict(item, **metadata) for item in result]
    except:
        print("\n\nERROR ### Here is the buggy response: ", response, "\n\n")
        result = None
    return result


def graphPrompt(input: str, metadata={}, model="mistral-openorca:latest"):
    if model == None:
        model = "mistral-openorca:latest"

    SYS_PROMPT = (
        "You are a network graph maker who extracts terms and their relations from a given context to create a detailed and comprehensive knowledge graph. "
        "You are provided with a context chunk (delimited by ) Your task is to extract an extensive ontology "
        "of terms and their interconnections mentioned in the given context. These terms should represent all key concepts, sub-concepts, and their relationships. \n"
        "Thought 1: While analyzing each sentence, extract all possible key terms and concepts:\n"
            "\tTerms may include objects, entities, locations, organizations, persons, \n"
            "\tconditions, acronyms, documents, services, concepts, processes, events, attributes\n"
            "\tBreak down complex terms into atomic components while maintaining their relationships\n"
            "\tIdentify implicit concepts that are important for understanding the context\n\n"
        "Thought 2: Establish comprehensive relationships between terms:\n"
            "\tIdentify direct and indirect relationships between terms\n"
            "\tConsider hierarchical relationships (is-a, part-of)\n"
            "\tIdentify causal relationships (causes, influences, enables)\n"
            "\tConsider temporal relationships (precedes, follows, during)\n"
            "\tMap semantic relationships (similar-to, different-from)\n"
            "\tEach term can have multiple relationships with other terms\n\n"
        "Thought 3: Provide detailed relationship descriptions:\n"
            "\tExplain how terms are related in detail\n"
            "\tInclude context-specific information\n"
            "\tDescribe the nature and strength of relationships\n\n"
        "Format your output as a list of json. Each element should contain detailed relationship information:\n"
        "[\n"
        "   {\n"
        '       "node_1": "A concept from extracted ontology",\n'
        '       "node_2": "A related concept from extracted ontology",\n'
        '       "edge": "detailed description of the relationship between the two concepts",\n'
        '       "relationship_type": "category of relationship (hierarchical/causal/temporal/semantic)",\n'
        '       "strength": "strength of relationship (strong/medium/weak)",\n'
        '       "bidirectional": true/false,\n'
        '       "context": "specific context where this relationship is valid"\n'
        "   }\n"
        "]"
    )

    USER_PROMPT = f"context: {input}``` \n\n output: "
    response, _ = client.generate(model_name=model, system=SYS_PROMPT, prompt=USER_PROMPT)
    try:
        result = json.loads(response)
        result = [dict(item, **metadata) for item in result]
    except:
        print("\n\nERROR ### Here is the buggy response: ", response, "\n\n")
        result = None
    return result