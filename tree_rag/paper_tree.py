import os
import regex as re
from langchain.text_splitter import LatexTextSplitter

class PaperTree:
    def __init__(self, title: str, text: str, abstract: str = None, parent = None, depth: int = 0, section_max_tokens: int = 300):
        self.title = title
        self.abstract = abstract
        self.text = text
        self.section_max_tokens = section_max_tokens
        self.section_max_chars = section_max_tokens * 4 # Average chars per token
        self.parent = parent
        self.depth = depth

        self.sections = self.split_to_sections(self.text)

    def __repr__(self):
        string = ""
        if self.depth > 0:
            string += "--"*(self.depth) + ">"
        string += self.title + "\n"
        for section in self.sections:
            string += section.__repr__()
        return string

    def split_to_sections(self, text: str):
        
        # First, search for any subsections to further split document into
        pattern = r"(\\" + "sub" * self.depth + r"section\s*({(?:[^{}]*+|(?2))*}))"
        matches = re.finditer(pattern, text)
        sections = []
        start, title = 0, "Headers"
        for match in matches:
            end = match.start()
            section_text = text[start : end]
            if section_text.strip() == "":
                continue
            sections.append(PaperTree(
                title = title, 
                text = section_text,
                    abstract = None, 
                    parent = self, 
                    depth = self.depth + 1, 
                    section_max_tokens = self.section_max_tokens,
            ))
            start, title = match.end(), match.group(2)[1:-1]
        if len(sections) > 0:
            section_text = text[start:]
            if not (section_text.strip() == ""):
                sections.append(PaperTree(
                    title = title, 
                    text = section_text, 
                    abstract = None, 
                    parent = self, 
                    depth = self.depth + 1, 
                    section_max_tokens = self.section_max_tokens,
                ))
            return sections
        
        # If no subsections were found, but the number of chars in text is much greater than section_max_chars
        elif len(self.text.strip()) > 2 * self.section_max_chars:
            text_splitter = LatexTextSplitter(chunk_size = self.section_max_chars, chunk_overlap = self.section_max_chars // 10, strip_whitespace=True)
            chunks = text_splitter.split_text(self.text)
            if len(chunks) > 1:
                sections = []
                for i, chunk in enumerate(chunks):
                    sections.append(PaperTree(
                        title = f"Chunk {i}", 
                        text = chunk, 
                        abstract = None, 
                        parent = self, 
                        depth = self.depth + 1,
                    ))
                return sections
        
        # No subsections needed
        return []
    