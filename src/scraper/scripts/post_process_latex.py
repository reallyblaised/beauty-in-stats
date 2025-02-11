import re

def remove_latex_commands(text):
    """Remove LaTeX commands and environments that are boilerplate"""
    # Remove document class, packages and other preamble
    text = re.sub(r'\\documentclass.*?\n', '', text)
    text = re.sub(r'\\usepackage.*?\n', '', text)
    text = re.sub(r'\\def\\.*?\n', '', text)
    
    # Remove author list and affiliations
    text = re.sub(r'\\begin{flushleft}.*?\\end{flushleft}', '', text, flags=re.DOTALL)
    
    # Remove bibliography and references
    text = re.sub(r'\\bibliographystyle{.*?}', '', text)
    text = re.sub(r'\\bibliography{.*?}', '', text)
    text = re.sub(r'\\~cite{.*?}', '', text)
    
    # Remove appendices
    text = re.sub(r'\\begin{appendices}.*?\\end{appendices}', '', text, flags=re.DOTALL)
    
    return text

def expand_symbols(text, symbol_map):
    """
    Expand LHCb shorthand symbols using the provided mapping
    symbol_map should be a dict of {shorthand: expanded_form}
    """
    for shorthand, expanded in symbol_map.items():
        # Handle both \command and \command{args} forms
        pattern = f'\\\\{shorthand}(?![a-zA-Z])'
        text = re.sub(pattern, expanded, text)
        
        pattern_with_args = f'\\\\{shorthand}{{(.*?)}}'
        text = re.sub(pattern_with_args, f'{expanded}\\1', text)
        
    return text

def remove_content_before_intro(text):
    """
    Remove all content before the Introduction section.
    """
    intro_patterns = [
        r'\\section{Introduction}',
        r'\\section\*{Introduction}',
    ]
    
    # Find the earliest Introduction section
    start_pos = None
    for pattern in intro_patterns:
        match = re.search(pattern, text)
        if match and (start_pos is None or match.start() < start_pos):
            start_pos = match.start()
    
    if start_pos is not None:
        return text[start_pos:]
    return text

def find_collab_section(text):
    """
    Find the LHCb collaboration section start and appropriate end point.
    Returns (start_pos, end_pos) or None if not found.
    """
    # Various patterns that might indicate the start of collaboration section
    collab_patterns = [
        r'\\centerline\s*{\s*\\large\s*\\bf\s*LHCb collaboration\s*}',
        r'\\begin{center}\s*\\large\s*\\bf\s*LHCb collaboration',
        r'\\section\*?\{LHCb collaboration\}'
    ]
    
    # Find the earliest match among all patterns
    start_pos = None
    for pattern in collab_patterns:
        match = re.search(pattern, text)
        if match and (start_pos is None or match.start() < start_pos):
            start_pos = match.start()
    
    if start_pos is None:
        return None
    
    # Look for end markers after the start position
    end_markers = [
        r'\\begin\s*{appendices}',
        r'\\section\*?\{Appendix',
        r'\\appendix'
    ]
    
    # Find the earliest end marker after start_pos
    end_pos = len(text)
    text_after_start = text[start_pos:]
    
    for marker in end_markers:
        match = re.search(marker, text_after_start)
        if match:
            possible_end = start_pos + match.start()
            end_pos = min(end_pos, possible_end)
    
    return (start_pos, end_pos)

def remove_section_content(text, section_names):
    """
    Remove all content between a section command containing section_name and the next section command
    or end of document.
    """
    # First remove everything before Introduction
    text = remove_content_before_intro(text)
    
    # Create a pattern that matches any section command followed by the section name
    # This handles \section, \section*, \subsection, etc.
    section_pattern = r'\\(?:sub)*section\*?{([^}]*)}'
    
    # Pattern for page breaks
    page_break_pattern = r'\\(?:new|clear)page'
    
    # Find all sections in the document
    sections = list(re.finditer(section_pattern, text))
    
    # Process regular sections
    regions_to_remove = []
    for i, match in enumerate(sections):
        section_name = match.group(1)
        
        if any(name.lower() in section_name.lower() for name in section_names):
            start_pos = match.start()
            
            # Find the earliest ending point
            end_pos = len(text)
            
            # Check for next section
            if i < len(sections) - 1:
                end_pos = min(end_pos, sections[i + 1].start())
            
            # Check for page breaks
            page_break_match = re.search(page_break_pattern, text[start_pos:])
            if page_break_match:
                possible_end = start_pos + page_break_match.start()
                end_pos = min(end_pos, possible_end)
            
            print(f"\nFound section to remove: {section_name}")
            print(f"Position: {start_pos} to {end_pos}")
            regions_to_remove.append((start_pos, end_pos))
    
    # Handle collaboration section
    collab_region = find_collab_section(text)
    if collab_region:
        start_pos, end_pos = collab_region
        print("\nFound collaboration section:")
        print(f"Position: {start_pos} to {end_pos}")
        regions_to_remove.append((start_pos, end_pos))
    
    # Remove all regions in reverse order
    cleaned_content = text
    for start, end in sorted(regions_to_remove, reverse=True):
        cleaned_content = cleaned_content[:start] + cleaned_content[end:]
    
    # Clean up multiple newlines
    cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)
    
    return cleaned_content.strip()

def clean_text(text, symbol_map, sections_to_remove=None):
    """
    Main cleaning function
    
    Args:
        text (str): Input LaTeX text
        symbol_map (dict): Mapping of symbols to expand
        sections_to_remove (list): List of section names whose content should be removed
    """
    # First remove boilerplate LaTeX
    text = remove_latex_commands(text)
    
    # Remove content of specified sections
    text = remove_section_content(text, sections_to_remove)
    
    # # Expand symbols using the mapping
    # text = expand_symbols(text, symbol_map)
    
    # # Remove remaining LaTeX formatting
    # text = re.sub(r'\\begin{document}', '', text)
    # text = re.sub(r'\\end{document}', '', text)
    # text = re.sub(r'\\section{.*?}', '', text)
    # text = re.sub(r'\\subsection{.*?}', '', text)
    
    # # Remove extra whitespace
    # text = re.sub(r'\n\s*\n', '\n\n', text)
    # text = text.strip()
    
    return text

# Example symbol map - extend this with the full LHCb mapping
SYMBOL_MAP = {
    'lhcb': 'LHCb',
    'mev': 'MeV',
    'gev': 'GeV',
    'jpsi': 'J/ψ',
    'Bz': 'B⁰',
    'Bp': 'B⁺',
    'Bm': 'B⁻',
    'epem': 'e⁺e⁻',
    'mumu': 'μ⁺μ⁻',
    # Add more mappings as needed
}

def process_file(input_file, output_file, sections_to_remove=None):
    """
    Process a LaTeX file, cleaning it and optionally removing specified sections
    
    Args:
        input_file (str): Path to input LaTeX file
        output_file (str): Path to output cleaned file
        sections_to_remove (list): Optional list of section names whose content should be removed
    """
    with open(input_file, 'r') as f:
        text = f.read()
        
    cleaned = clean_text(text, SYMBOL_MAP, sections_to_remove)
    
    with open(output_file, 'w') as f:
        f.write(cleaned)


if __name__ == '__main__':
    sections_to_remove = ['Acknowledgements', 'References']
    process_file(
        '/Users/blaisedelaney/PersonalProjects/beauty-in-stats/data/expanded_tex/2212.09153.tex',
        'test_cleaned.tex', 
    sections_to_remove)