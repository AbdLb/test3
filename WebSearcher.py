import nest_asyncio
nest_asyncio.apply()
import os
import boto3
from langchain_community.llms.bedrock import Bedrock
from langchain_core.output_parsers import BaseOutputParser
from typing import List
import re
from dotenv import load_dotenv
from duckduckgo_search import AsyncDDGS
import asyncio

load_dotenv()


aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.getenv('AWS_SESSION_TOKEN')

bedrock = boto3.client(service_name='bedrock-runtime',
region_name='eu-central-1',
aws_access_key_id=aws_access_key_id,
aws_secret_access_key=aws_secret_access_key,
aws_session_token=aws_session_token)

llm_claude1 = Bedrock(client=bedrock, model_id="anthropic.claude-instant-v1")

class QuestionListOutputParser(BaseOutputParser[List[str]]):
    """Output parser for a list of numbered questions. This parser
    will be used to formate the output of the LLM to generate queries"""
    def parse(self, text: str) -> List[str]:
        lines = re.findall(r"\d+\..*?(?:\n|$)", text)
        return lines

class DuckDuckGoSearchManager():
    def __init__(self, entity_name: str, num_results: int, key_words: str, llm):
        # logging.info("Initializing DuckDuckGoSearchManager.")
        self.entity_name = entity_name
        self.num_results = num_results
        self.key_words = key_words
        self.llm = llm
    
    def build_queries(self):
        
        # logging.debug("Building search queries.")
        '''
        template = f"""
           You are an assistant tasked to generate web search results to have all news if the {self.entity_name} is involved in {self.key_words}, fraud corruption and financial crimes.

           The result of these questions in websearch should give us sanctions in UK, Switzerland, US and UE.
           
           Improve this query only if the entity is not incomplete: entity illegal activites.

           The first should be formatted like: {self.entity_name} illegal activites.

           The output should be a numbered list of two search queries.
            \
            
           """]
        prompt = PromptTemplate(template=template, input_variables=['entity', 'key_words'])
        llmchain = LLMChain(prompt=prompt, llm=self.llm, output_parser=QuestionListOutputParser())
        results = llmchain({'entity': self.entity_name, 'key_words': self.key_words})
        logging.debug(f"Generated queries: {results['text']}")
        '''

        results = [f"""1.{self.entity_name} fraud, corruption """,
                   f"""3. illegal activities {self.entity_name} """,
                   f"""6. sanctions against {self.entity_name} """]
        
        print(results)

        return results
    
    def clean_search_query(self, query: str) -> str:
        """ Returns clean queries given by the LLM
            Args:
        query (str): A string representing the raw search query that needs cleaning.

            Returns:
        str: A cleaned and formatted version of the input query.
        """
        if query[0].isdigit():
            query = query[2:]
            first_quote_pos = query.find('"')
            if first_quote_pos == 2:
                query = query[first_quote_pos + 1 :]
                if query.endswith('"'):
                    query = query[:-1]
        cleaned_query = query.strip()
        return cleaned_query
    

    async def search_tool(self, query: str) -> List[dict]:
        """
        Performs a search using the DuckDuckGo search API and returns the results.
        Args:
            query (str): The raw search query string.

        Returns:
            List[dict]: A list of dictionaries, each representing a search result.
        """

        search_query = self.clean_search_query(query)
        results = await AsyncDDGS(proxy=None).text(
            keywords=search_query,
            region='wt-wt',
            safesearch='off',
            max_results=self.num_results
        )

        #filtered_results=[]
        #for doc in results:
        #    if self.entity_name in doc['body']:
        #        filtered_results.append(doc)
        #return filtered_results

        return results

    async def perform_search(self) -> List[dict]:
        """    
        This function constructs multiple queries, performs a search for each, and collates the unique
         results into a single list to avoid duplicates.

        Returns:
        List[dict]: A list of unique search result pages as dictionaries.

        """
        queries = self.build_queries()
        tasks = [self.search_tool(query) for query in queries]
        search_results = await asyncio.gather(*tasks)
        results = []
        for docs in search_results:
            results.extend([res for res in docs if res not in results])
        return results


async def main():
    key_words = "fraud, corruption, illegal activities"
    search_manager = DuckDuckGoSearchManager("Petrobras", num_results=2, key_words=key_words, llm=llm_claude1)
    results = await search_manager.perform_search()
    print(results)

if __name__ == "__main__":
    asyncio.run(main())

