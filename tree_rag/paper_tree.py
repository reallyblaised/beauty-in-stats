import os
import regex as re
import math
from langchain.text_splitter import TokenTextSplitter

# ~~ Paper Tree ~~ #

# If the number of chunks in a chunked section would be greater than MAX_CHUNKS, then split the section into equally sized subsections which are sufficiently small
MAX_CHUNKS = 8

class PaperTree:
    def __init__(self, title: str, text: str, abstract: str = None, parent = None, section_max_tokens: int = 250, keep_splitting: bool = True):
        self.title = title
        self.abstract = abstract
        self.text = text
        self.section_max_tokens = section_max_tokens
        self.parent = parent
 
        self.sections = []
        if keep_splitting:
            self.sections = self.split_to_sections(self.text)
        
        if len(self.sections) == 0 and self.abstract is None:
            self.abstract = self.text

    def __repr__(self):
        string = self._id_str() + "\n"
        for section in self.sections:
            string += section._tree_str()
        return string

    def get_depth(self):
        if self.parent == None:
            return 0
        else:
            return 1 + self.parent.get_depth()

    def _id_str(self):
        string = self.title
        parent = self.parent
        while parent is not None:
            string = f"{parent.title} --> {string}"
            parent = parent.parent
        return string
    
    def _tree_str(self):
        string = ("--"*self.get_depth()) + f"> {self.title}\n"
        for section in self.sections:
            string += section._tree_str()
        return string   

    def split_to_sections(self, text: str):
        sections = []

        # Search for an appendix and split document if found
        pattern = r"\\appendix\s"
        matches = list(re.finditer(pattern, text))
        if len(matches) > 0:
            match = matches[-1]
            start = match.start()
            end = match.end()
            body_text = text[:start]
            appendix_text = text[end:]
            sections.extend(self.split_to_sections(body_text))
            sections.append(PaperTree(
                title = "Appendix", 
                text = appendix_text,
                    abstract = None,
                    parent = self,
                    section_max_tokens = self.section_max_tokens,
            ))
            return sections

        # Search for any sections/subsections/subsubsections/etc to split document into
        for depth in range(self.get_depth() + 1):
            pattern = r"(\\" + "sub" * depth + r"section[\*\s]*(?:\[[^\]]*\])?\s*({(?:[^{}]*+|(?2))*}))"
            matches = re.finditer(pattern, text)
            start, title = 0, "Headers"
            for match in matches:
                end = match.start()
                section_text = text[start : end]
                sections.append(PaperTree(
                    title = title, 
                    text = section_text,
                        abstract = None, 
                        parent = self,
                        section_max_tokens = self.section_max_tokens,
                ))
                start, title = match.end(), match.group(2)[1:-1]
            if len(sections) > 0:
                section_text = text[start:]
                sections.append(PaperTree(
                    title = title, 
                    text = section_text, 
                    abstract = None, 
                    parent = self,
                    section_max_tokens = self.section_max_tokens,
                ))
                return sections

        # First, search for all elements (figures, tables, etc) in the paper
        elements = {}
        for element in ["figure", "table", "sidewaystable"]:
            pattern = r"\\begin\{" + element + r"\*?\}(.*?)\\end\{" + element + r"\*?\}"
            matches = re.findall(pattern, text, re.DOTALL)
            elements[element] = []
            for match in matches:
                elements[element].append(match)
            text = re.sub(pattern, "", text, flags=re.DOTALL)
        for key in elements:
            element_list = elements[key]
            for i, element in enumerate(element_list):
                abstract = ""
                for caption_type in ["caption", "tbl", "tabcaption"]:
                    pattern = r"\\" + caption_type + "[\*\s]*(?:\[[^\]]*\])?\s*({(?:[^{}]*+|(?1))*})"
                    abstract += "".join(re.findall(pattern, element, re.DOTALL))
                pattern = r"\\captionof[\*\s]*{\s*" + key + "\s*}\s*({(?:[^{}]*+|(?1))*})"
                abstract += "".join(re.findall(pattern, element, re.DOTALL))
                sections.append(PaperTree(
                    title = f"{key} {i}",
                    text = element,
                    abstract = abstract,
                    parent = self,
                    section_max_tokens = self.section_max_tokens,
                    keep_splitting = False,
        ))

        # Splitting the text (after all elements removed)
        text_splitter = TokenTextSplitter(
            chunk_size = self.section_max_tokens, 
            chunk_overlap = self.section_max_tokens // 8, # Overlap of 10-20% is standard
            strip_whitespace=True,
        )
        chunks = text_splitter.split_text(text)
        
        # If the number of chunks is greater than MAX_CHUNKS, then further split the text into subsections
        if len(chunks) > MAX_CHUNKS:
            num_sections = min(math.ceil(len(chunks) / (MAX_CHUNKS - 1)), MAX_CHUNKS)
            step = math.ceil(len(chunks) / num_sections)
            start_index = 0
            count = 0
            for i in range(0, len(chunks), step):
                i_end = i + step
                if i_end >= len(chunks):
                    end_index = None
                    section_text = text[start_index : ]
                else:
                    end_index = text.find(chunks[i + step])
                    section_text = text[start_index : end_index]
                sections.append(PaperTree(
                    title = f"Subsection {count}",
                    text = section_text,
                    abstract = None,
                    parent = self,
                    section_max_tokens = self.section_max_tokens,
                ))
                start_index = end_index
                count += 1
            return sections

        # Otherwise, if number of chunks is greater than 1 then split the text into chunks as-is
        if len(chunks) > 1:
            for i, chunk in enumerate(chunks):
                sections.append(PaperTree(
                    title = f"Chunk {i}", 
                    text = chunk, 
                    abstract = None, 
                    parent = self,
                    section_max_tokens = self.section_max_tokens,
                ))
            return sections
        
        # In case of only one chunk, keep the remaining text with all elements removed only if its longer than MIN_SECTION_LENGTH characters (not including white space)
        elif len(sections) > 0 and len(re.sub(r"\s+", "", text)) > MIN_SECTION_LENGTH:
            sections.append(PaperTree(
                title = "Chunk 0",
                text = text,
                abstract = None,
                parent = self,
                section_max_tokens = self.section_max_tokens
            ))
        
        return sections
    

# ~~ Helper Functions ~~ #

# Remove any sections from a PaperTree which are less than MIN_SECTION_LENGTH characters long.
MIN_SECTION_LENGTH = 50
def remove_empty_sections(paper):
    new_sections = []
    modified = False
    for section in paper.sections:
        if len(re.sub("\s", "", section.text)) < MIN_SECTION_LENGTH:
            modified = True
        else:
            new_sections.append(section)
    if modified:
        paper.sections = new_sections

    for section in paper.sections:
        remove_empty_sections(section)

# Letter papers are not split properly, because they often do not contain the \section{...} command. Thus, normally the entire content of the paper gets sucked into the 'Headers' section
# and the first section afterwards is the Aknowledgements section. This function simply expands and removes any 'Headers' section with a large number of subsections.
def fix_letter_subsections(paper):
    new_sections = []
    changed = False
    for section in paper.sections:
        if section.title in "Headers":
            subsections = section.sections
            if len(subsections) > 0 and all(["Subsection" in subsection.title for subsection in subsections]):
                changed = True
                for subsection in subsections:
                    new_sections.append(subsection)
                    subsection.parent = paper
        else:
            new_sections.append(section)
    if changed:
        paper.sections = new_sections

# For any section with one lone subsection, collapse that section into the subsection
def collapse_lone_subsections(paper):
    new_sections = []
    changed = False
    for section in paper.sections:
        subsections = section.sections
        if len(subsections) == 1:
            changed = True
            for subsection in subsections:
                new_sections.append(subsection)
                subsection.parent = paper
                subsection.title = f"{section.title} - {subsection.title}"
        else:
            new_sections.append(section)
    if changed == True:
        paper.sections = new_sections

    for section in paper.sections:
        collapse_lone_subsections(section)

# Helper function to clean up LaTeX and LHCb junk before splitting into PaperTrees
def clean_junk(tex):
    # Start the cleanup after the abstract or titlepage
    substrings = ["\\maketitle", "\\end{titlepage}", "\\end{abstract}", "\\abstract"]
    max_index = 0
    for substring in substrings:
        index = tex.rfind(substring) + len(substring)
        if index > max_index:
            max_index = index
    tex = tex[max_index:]

    patterns = [
        r"\\newpage", r"\\cleardoublepage", r"\\pagestyle\{[\w\d]+\}",  r"\\setcounter\{[\w\d]+\}\{\d+\}", 
        r"\\pagenumbering\{[\w\d]+\}", r"\\bibliographystyle\{[\w\d]+\}", r"\\end\{document\}", r"\\bibliography",
    ]
    for pattern in patterns:
        tex = re.sub(pattern, "", tex)

    # Remove all macros
    pattern = r"\\def\s*\\(\w+)\s*((?:#\d\s*)*)\s*({(?:[^{}]*+|(?3))*})"
    tex = re.sub(pattern, "", tex)
    pattern = r"\\newcommand\*?\s*{?\s*\\(\w+)\s*}?\s*((?:\[\s*\d+\s*\])*)\s*({(?:[^{}]*+|(?3))*})"
    tex = re.sub(pattern, "", tex)
    pattern = r"\\renewcommand\*?\s*{?\s*\\(\w+)\s*}?\s*((?:\[\s*\d+\s*\])*)\s*({(?:[^{}]*+|(?3))*})"
    tex = re.sub(pattern, "", tex)
    
    # Remove all comments
    pattern = r"\\begin\s*\{\s*comment\s*\}(.*?)\\end\s*\{\s*comment\s*\}"
    tex = re.sub(pattern, "", tex, flags=re.DOTALL)
    pattern = r"(?<!\\)%.*"
    tex = re.sub(pattern, "", tex)

    # Get rid of any bibliography
    pattern = r"\\bibitem\{.+\}(?:.|\n)*\\EndOfBibitem"
    tex = re.sub(pattern, "", tex)
    pattern = r"\\begin{thebibliography}(?:\n|.)*\\end{thebibliography}"
    tex = re.sub(pattern, "", tex)

    # LHCb junk
    pattern = r"\\centerline[\n\s]*\{[\n\s]*\\large[\n\s]*\\bf[\n\s]*LHCb[\n\s]*collaboration[\n\s]*\}[\n\s]*\\begin[\n\s]*\{[\n\s]*flushleft[\n\s]*\}(?:\n|.)*\{[\n\s]*\\footnotesize(?:\n|.)*\}[\n\s]*\\end[\n\s]*\{[\n\s]*flushleft[\n\s]*\}"
    tex = re.sub(pattern, "", tex)
    pattern = r"[a-zA-Z.-]+(?:~[a-zA-Z-\\ \{\}\"\'\`]*)+\$\^\{[a-zA-Z0-9,]+\}\$[\,.][\s\n]*"
    tex = re.sub(pattern, "", tex)
    pattern = r"\$\s*\^\{[\w\d\s]+\}\$.*\\"
    tex = re.sub(pattern, "", tex)

    # Remove excess whitespace
    pattern = r"\s{2,}"
    tex = re.sub(pattern, " ", tex)

    return tex