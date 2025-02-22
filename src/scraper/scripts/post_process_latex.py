import regex as re
import csv
import expand_latex_macros
import os

def remove_headers(tex):
    """
    Remove all content before the abstract or titlepage
    """
    substrings = ["\\maketitle", "\\end{titlepage}", "\\end{abstract}", "\\abstract"]
    max_index = 0
    for substring in substrings:
        index = tex.rfind(substring) + len(substring)
        if index > max_index:
            max_index = index
    return tex[max_index:]

def remove_boilerplate(tex):
    """
    Remove all LaTeX boilerplate code, comments, and bibliographies
    """
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
    
    return tex

def remove_lhcb_content(tex):
    """
    Remove all LHCb collab sections, lists of universities, etc
    """
    # LHCb junk
    pattern = r"\\centerline[\n\s]*\{[\n\s]*\\large[\n\s]*\\bf[\n\s]*LHCb[\n\s]*collaboration[\n\s]*\}[\n\s]*\\begin[\n\s]*\{[\n\s]*flushleft[\n\s]*\}(?:\n|.)*\{[\n\s]*\\footnotesize(?:\n|.)*\}[\n\s]*\\end[\n\s]*\{[\n\s]*flushleft[\n\s]*\}"
    tex = re.sub(pattern, "", tex)
    pattern = r"[a-zA-Z.-]+(?:~[a-zA-Z-\\ \{\}\"\'\`]*)+\$\^\{[a-zA-Z0-9,]+\}\$[\,.][\s\n]*"
    tex = re.sub(pattern, "", tex)
    pattern = r"\$\s*\^\{[\w\d\s]+\}\$.*\\"
    tex = re.sub(pattern, "", tex)
    return tex

def remove_section_content(tex, section_names):
    """
    Remove all content between a section command containing section_name and the next section command
    or end of document.
    """
    # Create a pattern that matches any section command followed by the section name
    # This handles \section, \section*, \subsection, etc.
    section_pattern = r'\\(?:sub)*section\*?{([^}]*)}'
    
    # Pattern for page breaks
    page_break_pattern = r'\\(?:new|clear)page'
    
    # Find all sections in the document
    sections = list(re.finditer(section_pattern, tex))
    
    # Process regular sections
    regions_to_remove = []
    for i, match in enumerate(sections):
        section_name = match.group(1)
        
        if any(name.lower() in section_name.lower() for name in section_names):
            start_pos = match.start()
            
            # Find the earliest ending point
            end_pos = len(tex)
            
            # Check for next section
            if i < len(sections) - 1:
                end_pos = min(end_pos, sections[i + 1].start())
            
            # Check for page breaks
            page_break_match = re.search(page_break_pattern, tex[start_pos:])
            if page_break_match:
                possible_end = start_pos + page_break_match.start()
                end_pos = min(end_pos, possible_end)
            
            print(f"\nFound section to remove: {section_name}")
            print(f"Position: {start_pos} to {end_pos}")
            regions_to_remove.append((start_pos, end_pos))
    
    # Remove all regions in reverse order
    cleaned_content = tex
    for start, end in sorted(regions_to_remove, reverse=True):
        cleaned_content = cleaned_content[:start] + cleaned_content[end:]
    return cleaned_content.strip()

current_directory = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_directory, 'lhcb_symbols.csv'), mode='r') as file:
    reader = csv.reader(file)
    lhcb_symbols = next(reader)

def clean_tex(tex, sections_to_remove=None):
    """
    Main cleaning function
    
    Args:
        tex (str): Input LaTeX tex
        sections_to_remove (list): List of section names whose content should be removed
    """
    tex = expand_latex_macros.expand_latex_macros(tex, commands_dont_expand=lhcb_symbols)
    tex = remove_headers(tex)
    tex = remove_boilerplate(tex)
    tex = remove_lhcb_content(tex)
    tex = remove_section_content(tex, sections_to_remove)
    # Remove excessive newlines
    tex = re.sub(r"\n[\s]+", "\n", tex)
    return tex

def process_file(input_file, output_file, sections_to_remove=None):
    """
    Process a LaTeX file, cleaning it and optionally removing specified sections
    
    Args:
        input_file (str): Path to input LaTeX file
        output_file (str): Path to output cleaned file
        sections_to_remove (list): Optional list of section names whose content should be removed
    """

    print("Input File: " , input_file)

    with open(input_file, 'r') as f:
        tex = f.read()

    cleaned = clean_tex(tex, sections_to_remove)
    
    with open(output_file, 'w') as f:
        f.write(cleaned)


if __name__ == '__main__':
    sections_to_remove = ['Acknowledgements', 'References']
    process_file(
        '/work/submit/mcgreivy/beauty-in-stats/src/scraper/data/expanded_tex/2501.12611.tex',
        'test_cleaned.tex', 
    sections_to_remove)