import asyncio
import json
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.tools import Tool
import neo4j
from typing import List, Dict, Any
# import os


class AsyncKnowledgeGraph:
    """
    Async Knowledge Graph handles the core graph operations with non-blocking calls
    """
    
    def __init__(self, uri, user, password):
        """Initialize the Knowledge Graph with Neo4j connection"""
        self.driver = neo4j.AsyncGraphDatabase.driver(
            uri, auth=(user, password)
        )
    
    async def create_entity(self, entity_type: str, properties: Dict[str, Any]):
        """Create a new entity node in the knowledge graph"""
        async with self.driver.session() as session:
            # convert properties to cypher parameters
            props_string = ", ".join([f"{k}: ${k}" for k in properties.keys()])
            
            # create the entity
            result = await session.run(
                f"CREATE (e:{entity_type} {{{props_string}}}) RETURN e",
                **properties
            )
            record = await result.single()
            return f"Created {entity_type} entity with ID: {record['e'].id}"
    
    async def get_entity(self, entity_type: str, properties: Dict[str, Any]):
        """Get an entity from the knowledge graph"""
        async with self.driver.session() as session:
            # build match clause
            props_str = " AND ".join([f"e.{k} = ${k}" for k in properties.keys()])
            
            # query to find the entity
            query = f"""
            MATCH (e:{entity_type})
            WHERE {props_str}
            RETURN e
            """
            
            result = await session.run(query, **properties)
            record = await result.single()
            return record['e'] if record else None
    
    async def create_relationship(self, from_type: str, from_props: Dict[str, Any], 
                           rel_type: str, to_type: str, to_props: Dict[str, Any], 
                           rel_props: Dict[str, Any] = None):
        """Create a relationship between two entities"""
        async with self.driver.session() as session:
            # build match clauses for the entities
            from_props_str = " AND ".join([f"a.{k} = ${k}" for k in from_props.keys()])
            to_props_str = " AND ".join([f"b.{k} = ${k}" for k in to_props.keys()])
            
            # build properties for the relationship
            rel_props_str = ""
            if rel_props:
                rel_props_str = " {" + ", ".join([f"{k}: ${k}" for k in rel_props.keys()]) + "}"
            
            # combine all parameters
            params = {**from_props, **to_props}
            if rel_props:
                params.update(rel_props)
            
            # create the relationship
            query = f"""
            MATCH (a:{from_type}), (b:{to_type})
            WHERE {from_props_str} AND {to_props_str}
            CREATE (a)-[r:{rel_type}{rel_props_str}]->(b)
            RETURN a, r, b
            """
            
            result = await session.run(query, **params)
            await result.consume()
            return f"Created relationship: ({from_type})-[{rel_type}]->({to_type})"
    
    async def query_graph(self, query: str, params: Dict[str, Any] = None):
        """Run a Cypher query against the knowledge graph"""
        async with self.driver.session() as session:
            result = await session.run(query, params or {})
            records = await result.fetch_all()
            return [dict(record) for record in records]
    
    async def get_related_entities(self, entity_type: str, properties: Dict[str, Any], depth: int = 1):
        """Get entities related to a specific entity up to a certain depth"""
        async with self.driver.session() as session:
            # build match clause
            props_str = " AND ".join([f"e.{k} = ${k}" for k in properties.keys()])
            
            # query to find related entities
            query = f"""
            MATCH path = (e:{entity_type})-[*1..{depth}]-(related)
            WHERE {props_str}
            RETURN related
            """
            
            result = await session.run(query, **properties)
            records = await result.fetch_all()
            return [record['related'] for record in records]
    
    async def initialize_schema(self):
        """Initialize the knowledge graph schema with constraints and indexes"""
        async with self.driver.session() as session:
            # create constraints
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Task) REQUIRE t.task_id IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE")
            
            # create indexes
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Task) ON (t.task_type)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Task) ON (t.status)")
            
            return "Schema initialized with constraints and indexes"
    
    async def close(self):
        """Close the Neo4j connection"""
        await self.driver.close()


class AsyncKnowledgeGraphAgent:
    """
    Async Knowledge Graph Agent uses the KnowledgeGraph and adds the agent capabilities with non-blocking operations
    """
    
    def __init__(self, knowledge_graph, llm=None):
        """Initialize the KG Agent with a KnowledgeGraph instance and LLM"""
        self.kg = knowledge_graph
        
        # Initialize LLM if not provided
        self.llm = llm or ChatOpenAI(temperature=0)
        
        # Create tools for the agent
        self.tools = self._create_tools()
        
        # Create the agent executor
        self.agent = self._create_agent()
    
    def _create_tools(self):
        """Create tools for the KG Agent to use"""
        # Create async tool wrappers
        async def create_entity_wrapper(entity_type, properties):
            return await self.kg.create_entity(entity_type, properties)
            
        async def create_relationship_wrapper(from_type, from_props, rel_type, to_type, to_props, rel_props=None):
            return await self.kg.create_relationship(from_type, from_props, rel_type, to_type, to_props, rel_props)
            
        async def query_graph_wrapper(query, params=None):
            return await self.kg.query_graph(query, params)
            
        async def get_related_entities_wrapper(entity_type, properties, depth=1):
            return await self.kg.get_related_entities(entity_type, properties, depth)
        
        tools = [
            Tool(
                name="create_entity",
                func=create_entity_wrapper,
                description="Create a new entity node in the knowledge graph"
            ),
            Tool(
                name="create_relationship",
                func=create_relationship_wrapper,
                description="Create a relationship between two entities in the knowledge graph"
            ),
            Tool(
                name="query_graph",
                func=query_graph_wrapper,
                description="Query the knowledge graph for information"
            ),
            Tool(
                name="get_related_entities",
                func=get_related_entities_wrapper,
                description="Get entities related to a specific entity in the knowledge graph"
            )
        ]
        return tools
    
    def _create_agent(self):
        """Create the agent executor"""
        system_message = SystemMessage(
            content="""You are GAZIE's Knowledge Graph Agent that automatically builds and maintains a knowledge graph.
            Your job is to:
            1. Identify entities and relationships from user tasks and activities
            2. Create and update the knowledge graph accordingly
            3. Learn domain-specific patterns over time
            4. Ensure the knowledge graph is accurate and up-to-date
            
            When processing new information, first check if related entities already exist,
            then update or create new nodes and relationships as needed.
            """
        )
        
        # Create the agent executor
        agent = AgentExecutor.from_agent_and_tools(
            agent=AgentType.OPENAI_FUNCTIONS,
            tools=self.tools,
            llm=self.llm,
            system_message=system_message,
            verbose=True
        )
        
        return agent
    
    async def extract_entities_from_task(self, task: Dict[str, Any]):
        """Extract entities and relationships from a task using system and user prompts"""
        
        system_prompt = PromptTemplate.from_template("""You are GAZIE's knowledge graph extraction engine. Your role is to analyze user tasks and extract structured information for workflow automation.

        Focus on identifying workflow-relevant entities:
        - Applications/Systems (Salesforce, QuickBooks, Email clients, etc.)
        - Data Sources (reports, files, databases, APIs)
        - Actions/Operations (generate, process, analyze, send, approve)
        - Outputs (reports, notifications, files, decisions)
        - Triggers (time-based, event-based, conditional)
        - People/Roles (recipients, approvers, stakeholders)

        Extract relationships that show workflow dependencies:
        - USES, GENERATES, TRIGGERS, DEPENDS_ON, SENDS_TO, PROCESSES

        Always return valid JSON only, no additional text or explanations.""")

        user_prompt = PromptTemplate.from_template("""Extract entities and relationships from this task for GAZIE's workflow automation:

        Task: {json.dumps(task, indent=2)}

        Return JSON in this exact format:
        {{
            "entities": [
                {{
                    "type": "entity_type",
                    "properties": {{
                        "name": "entity_name",
                        "category": "workflow_category",
                        "frequency": "how_often_used",
                        "automation_potential": "high/medium/low"
                    }}
                }}
            ],
            "relationships": [
                {{
                    "from_type": "entity_type1",
                    "from_props": {{"name": "entity_name1"}},
                    "rel_type": "RELATIONSHIP_TYPE",
                    "to_type": "entity_type2",
                    "to_props": {{"name": "entity_name2"}},
                    "rel_props": {{
                        "sequence_order": "step_number",
                        "conditions": "when_this_happens",
                        "automation_ready": "true/false"
                    }}
                }}
            ]
        }}""")

        # create messages for the LLM
        messages = [
            SystemMessage(content=system_prompt.format()),
            HumanMessage(content=user_prompt.format())
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # extract JSON from response
        try:
            extraction = json.loads(response.content)
            return extraction
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # fallback if JSON parsing fails
            return {"entities": [], "relationships": []}
    
    async def process_task(self, task: Dict[str, Any]):
        """Process a task to extract entities and relationships for the knowledge graph"""
        # extract entities and relationships
        extraction = await self.extract_entities_from_task(task)
        
        # create entities
        created_entities = []
        for entity in extraction.get("entities", []):
            try:
                result = await self.kg.create_entity(entity["type"], entity["properties"])
                created_entities.append(result)
            except Exception as e:
                print(f"Error creating entity: {e}")
        
        # create relationships
        created_relationships = []
        for rel in extraction.get("relationships", []):
            try:
                result = await self.kg.create_relationship(
                    rel["from_type"], rel["from_props"],
                    rel["rel_type"],
                    rel["to_type"], rel["to_props"],
                    rel.get("rel_props")
                )
                created_relationships.append(result)
            except Exception as e:
                print(f"Error creating relationship: {e}")
        
        return {
            "created_entities": created_entities,
            "created_relationships": created_relationships
        }
    
    async def learn_from_tasks(self, tasks: List[Dict[str, Any]]):
        """Learn from a batch of tasks"""
        results = []
        # process tasks concurrently for better performance
        tasks_to_process = [self.process_task(task) for task in tasks]
        results = await asyncio.gather(*tasks_to_process)
        return results
    
    async def answer_question(self, question: str):
        """Answer a question using the knowledge graph"""
        # use the agent to answer the question
        result = await self.agent.ainvoke({"input": question})
        return result