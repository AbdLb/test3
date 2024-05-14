import nest_asyncio
import dotenv

from langchain_community.document_loaders import WebBaseLoader
import boto3
from langchain_community.llms.bedrock import Bedrock
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from WebSearcher import DuckDuckGoSearchManager
import logging
import os
import time
from pydantic import BaseModel
from anthropic import AsyncAnthropicBedrock
import asyncio
nest_asyncio.apply()
dotenv.load_dotenv()

GOOGLE_CSE_ID=os.getenv('google_cse_id')
GOOGLE_API_KEY=os.getenv('google_api_key')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
aws_session_token = os.getenv('aws_session_token')

bedrock = boto3.client(service_name='bedrock-runtime',
region_name='eu-central-1',
aws_access_key_id=aws_access_key_id,
aws_secret_access_key=aws_secret_access_key,
aws_session_token=aws_session_token)

client = AsyncAnthropicBedrock(
    aws_access_key=aws_access_key_id,
    aws_secret_key=aws_secret_access_key,
    aws_session_token=aws_session_token,
    aws_region="us-east-1"
)

llm_claude1 = Bedrock(client=bedrock, model_id="anthropic.claude-instant-v1")

class DocumentProcessor:
    def __init__(self, entity, client, key_words):
        self.entity = entity
        self.docs = [] 
        self.is_loaded = False 
        self.client = client
        self.key_words=key_words

    async def initialize(self):
        self.search_manager = DuckDuckGoSearchManager(entity_name=self.entity, num_results=2, key_words=self.key_words, llm=llm_claude1)
        self.results = await self.search_manager.perform_search()
        print(self.results)
        self.urls = [result["href"] for result in self.results]
        self.load_documents()
        self.is_loaded = True

    def load_documents(self):
        """
        Loads asynchronously multiple documents from specified URLs for processing.
        """
        loader =  WebBaseLoader(self.urls, continue_on_failure=True)
        loader.requests_per_second = 5
        docs = loader.aload()
        self.docs = docs

    async def summarize_document(self, document):
        """
        Asynchronously summarizes a document to identify and report on elements that may pose KYC (Know Your Customer) risks.

        Args:
            document (str): The name or identifier of the document to be analyzed.

        Returns:
            str: The summarized content as generated by the language model, which includes identified risks and their context, formatted along with
                relevant URL links for easy verification.
        """


        content=f"""
        You are a professional KYC analyst who creates detailed summaries of web articles.
        
        Based on this document {document}, list:
        - All the information linked to sanctions taken against {self.entity} for illegal facts, fraud, corruption or similar facts.
        - All controversial facts, fraud, money evasion, illicit activities, and financial crimes {self.entity} is involved in.
        
        Also mention the country where these events are connected to determine if the entity might be linked to activities in countries known for incidents related to fraud, corruption.
        At the end of each entry, please add the URL of the article."""

        message = await self.client.messages.create(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            max_tokens=1256,
            messages=[{"role": "user", "content": content}]
        )
        return message.content
    
    async def generate_report(self, summaries) -> str:
        """
        Asynchronously generates a final, consolidated summary report based on multiple input summaries, focusing specifically on KYC (Know Your Customer) risk factors.
        Args:
            summaries (str): A string containing all the individual summaries that need to be consolidated into a final report.
        Returns:
            str: The consolidated summary as generated by the language model, formatted to include key risk-related facts and their corresponding URL links for easy reference and verification.
        """
        
        content = f""" You are a professional KYC analyst who generates well-structured analysis reports that are detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness.

        You are a professional KYC analyst who generates well-structured analysis reports that are detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness.

        After conducting a web search, we have these web pages {summaries} containing information extracted from the web. Please generate a very detailed report of:
        - All sanctions taken against {self.entity} that could pose a risk for a trading company. And if in you knowledge, you know sanctions taken for illegal facts, you must list some sanctions.

        - All relevant facts extracted and related/done by {self.entity} that are directly linked to fraud, corruption, illegal activities, etc.

        Use your existing knowledge and expertise to provide context and identify potential risks, making logical connections based on previous KYC analyses.

        If {self.entity} is not associated with any concerning facts, only return that it does not present a particular risk and do not include summaries of web pages about {self.entity}.

        Otherwise, return a detailed and well-organized final report that summarizes the information. For each piece of information, you must include the source link (URL) so that the reader can directly access the article.

        Begin the report with the sentence: "The web search report and the risk level:"
                
        At the end of the report, also include a sentence justifying the risk level. If there were sanctions, automatically set the risk level to "High."
        
        The last line should only contain one of these words describing the risk class: Low, Medium, or High. Do not add the word "Risk."
        """
        
        message = await self.client.messages.create(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            max_tokens=1256,
            messages=[{"role": "user", "content": content}]
        )
        return message.content[0].text

    async def summarize_documents(self):
        """
        Asynchronously summarizes multiple documents by executing multiple document summarization tasks in parallel
        
        Returns:
        List[str]: A list of strings where each string is a summary of one document, focusing on elements relevant to KYC (Know Your Customer) compliance risks.

        """
    
        tasks = [self.summarize_document(doc) for doc in self.docs]
        summaries = await asyncio.gather(*tasks)
        return summaries

    async def process_documents(self):
        """
        Asynchronously processes a series of documents to generate a consolidated report summarizing KYC risk-related information.

        Returns:
            str: A final consolidated report composed of key KYC risk-related information extracted and summarized from multiple documents.

        """
        if not self.is_loaded:
            await self.initialize()
        summaries = await self.summarize_documents()
        report = await self.generate_report(summaries)
        risk_class = report.split()[-1]
        return report, risk_class

async def KYCwebreport(entity, client):
    key_words='fraud, corruption, financial crimes'
    processor = DocumentProcessor(entity=entity, client=client, key_words=key_words)
    processed_docs = await processor.process_documents()
    return processed_docs

async def main():
    start=time.time()
    entity='Zidane'
    report, risk_class = await KYCwebreport(entity=entity, client=client)
    end=time.time()
    print(report)
    print(end-start)



if __name__ == "__main__":
    asyncio.run(main())