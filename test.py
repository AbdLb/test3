import nest_asyncio
import dotenv

from langchain_community.document_loaders import WebBaseLoader
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
import boto3
from langchain_community.chat_models import BedrockChat
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from WebSearcher import DuckDuckGoSearchManager
import logging
import os
import time
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from anthropic import AsyncAnthropicBedrock
import asyncio
nest_asyncio.apply()
dotenv.load_dotenv()

class Report(BaseModel):
    report: str = Field(description="final report")
    risk: str = Field(description="risk associated with the entity")

parser = JsonOutputParser(pydantic_object=Report)

GOOGLE_CSE_ID=os.getenv('google_cse_id')
GOOGLE_API_KEY=os.getenv('google_api_key')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
aws_session_token = os.getenv('aws_session_token')

bedrock = boto3.client(service_name='bedrock-runtime',
region_name='us-east-1',
aws_access_key_id=aws_access_key_id,
aws_secret_access_key=aws_secret_access_key,
aws_session_token=aws_session_token)

client = AsyncAnthropicBedrock(
    aws_access_key=aws_access_key_id,
    aws_secret_key=aws_secret_access_key,
    aws_session_token=aws_session_token,
    aws_region="us-east-1"
)

llm_claude3 = BedrockChat(client=bedrock, model_id="anthropic.claude-3-haiku-20240307-v1:0")

class DocumentProcessor:
    def __init__(self, entity, client, key_words):
        self.entity = entity
        self.docs = []
        self.is_loaded = False
        self.client = client
        self.key_words = key_words
        self.llm=llm_claude3

    async def initialize(self):
        self.search_manager = DuckDuckGoSearchManager(
            entity_name=self.entity, 
            num_results=2, 
            key_words=self.key_words, 
            llm=llm_claude3
        )
        self.results = await self.search_manager.perform_search()
        self.urls = [result["href"] for result in self.results]
        self.load_documents()
        self.is_loaded = True

    def load_documents(self):
        loader = WebBaseLoader(self.urls, continue_on_failure=True)
        loader.requests_per_second = 5
        docs = loader.aload()
        self.docs = docs

    async def summarize_document(self, document):
        template1 = """
        You are a professional KYC analyst who creates detailed summaries of web articles.
        
        Based on this document {document}, list:
        - All the information linked to sanctions taken against {entity}.
        - All controversial facts, fraud, money evasion, illicit activities, and financial crimes {entity} is involved in.
        
        Also mention the country where these events are connected to determine if the entity might be linked to activities in countries known for incidents related to fraud, corruption.
        At the end of each entry, please add the URL of the article.
        """
        prompt = PromptTemplate(template=template1, input_variables=['document', 'entity'])
        llmchain = LLMChain(prompt=prompt, llm=self.llm)
        results = await llmchain.ainvoke({'document': document, 'entity': self.entity})

        return results

    async def generate_report(self, summaries) -> str:
        template2 = """
        You are a professional KYC analyst who generates well-structured analysis reports that are detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness.

        After a web search, we have these web pages ({summaries}) containing information extracted from a web search. I need a very detailed report of:
        - All sanctions taken against {entity} that could be a risk for a trading company. If no information about sanctions is found, do not include this part in the report.
        - All relevant facts extracted and related/done by {entity} that are directly linked to fraud, corruption, illegal activities, etc.

        If {entity} is not associated with any concerning facts, only return that it does not present a particular risk and do not include summaries of web pages about {entity}.

        If this is not the case, return a detailed and well-organized final report that summarizes the information. Each piece of information should include the source link (URL) so that the reader can directly access the article.

        Begin the report with the sentence: "The web search report and the risk level:"
        
        At the end of the report, also include a sentence justifying the risk level. If there were sanctions, automatically set the risk level to "High."

        The last line should only contain one of these words describing the risk class: Low, Medium, or High. Do not add the word "Risk."
        """
        prompt = PromptTemplate(template=template2, input_variables=['summaries', 'entity', ], partial_variables={"format_instructions": report.get_format_instructions()},)
        llmchain = LLMChain(prompt=prompt, llm=self.llm)
        results = llmchain({'summaries': summaries, 'entity': self.entity})

        return results

    async def summarize_documents(self):
        tasks = [self.summarize_document(doc) for doc in self.docs]
        summaries = await asyncio.gather(*tasks)
        return summaries

    async def refine_report(self, report):
        """
        Refine the final report to remove unrelated entities.
        """
        template3 = """
        You are a professional KYC analyst:

        {report}

        Refine the report to remove unrelated entities and improve the format. Return only the refined improved report
        """
        prompt = PromptTemplate(template=template3, input_variables=['report'])
        llmchain = prompt | self.llm | parser
        results = llmchain({'report': report})

        return results

    async def process_documents(self):
        if not self.is_loaded:
            await self.initialize()
        summaries = await self.summarize_documents()
        report = await self.generate_report(summaries)
        refined_report = await self.refine_report(report)
        #risk_class = refined_report.split()[-1]
        return refined_report

async def KYCwebreport(entity, client):
    key_words='fraud, corruption, financial crimes'
    processor = DocumentProcessor(entity=entity, client=client, key_words=key_words)
    processed_docs = await processor.process_documents()
    return processed_docs

async def main():
    start=time.time()
    entity='Petrobras'
    report= await KYCwebreport(entity=entity, client=client)
    end=time.time()
    print(report)
    print(end-start)

if __name__ == "__main__":
    asyncio.run(main())