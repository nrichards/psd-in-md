import sys
from itertools import pairwise
from dataclasses import dataclass
import csv

from mistletoe.block_token import Paragraph, Table, Document
from mistletoe.markdown_renderer import MarkdownRenderer, BlankLine
from mistletoe.token import Token

from button_sequence import ButtonSequence
from constants import LABEL_OR_SECTION_CSV_HEADER, SECTION_KEY, LABEL_KEY, NAME_KEY, KEYWORD_N_KEY_COUNT, \
    KEYWORD_N_PREFIX_KEY, DEFAULT_NAME_KEY, SECTION_VALUE, LABEL_VALUE
from modify_md import validate_files
from util import ImageOpt, print_markdown_tree, find_category_names  # noqa: F401

# For debugging parsing
DEBUG_LOG_SEQS = True


def write_seqs_markdown(md_out_file, image_out_path, md_in_file, category_pattern_file,
                        button_sequences: [ButtonSequence], opt: ImageOpt):
    ws = WriteSequences()
    ws.write_seqs_markdown(md_out_file, image_out_path, md_in_file, category_pattern_file, button_sequences, opt)


@dataclass
class SequenceCategory:
    """Names and keywords to match to names, for categorizing sequences.
    
    Sequences can be categorized into high level Sections and lower level Labels. 
    The categorization process uses keywords, heuristically matched to a section/label name, from within the
    name of the sequence or the nearest organizing heading in the document."""
    is_section: bool
    name: str
    keywords: [str]
    is_default: bool


@dataclass
class Combo:
    """Maps sequences to matched categories."""
    seq: ButtonSequence
    found_categories: [str]


@dataclass
class Section:
    """Maps section to sequences."""
    name: str
    combos: [Combo]


class WriteSequences:
    # Accumulate the seqs for the next table, associating the labels with each seq: (seq, labels) 
    # Create a set of all labels
    # For each seq
    # Consider dumping multiple tables for a single section

    # Section 'Vinyl record scratch mode'
    # Found labels ['Edit', 'Scratch'] for desc: 'Record volume '
    # Found labels ['Scratch'] for desc: 'Record pan '
    # Found labels ['Edit', 'Looper'] for desc: 'Looper master volume '
    # Found labels ['Edit', 'Looper', 'Scratch'] for desc: 'Cross fade between Record volume and Looper volume '
    # Found labels ['Navigate', 'Mode'] for desc: 'Toggle between Monitor mode and Mixer '

    # iterate repeatedly, an ever shrinking list, until done
    # Look at label, find highest priority label (Scratch)
    # Add current to 'done' list
    # Look through remaining seqs, binning seqs unless their label is higher priority ( ? )
    # Edit Scratch Looper Navigate Mode
    # 3    3       2      1        1
    # -    yYY              
    # 3    3       2      1        1
    #      
    # 3    3       2      1        1
    #              y
    # 3    3       2      1        1
    # Scratch, Scratch, Looper, Looper, Mode, Navigate

    default_category = 'Perform'

    def write_seqs_markdown(self, md_out_file, image_out_path, md_in_file, category_pattern_file,
                            button_sequences: [ButtonSequence], opt: ImageOpt):
        """Create a Markdown file collecting just the button sequences, grouped and sub-grouped.
    
        :param category_pattern_file: 
        :return: 
        :param md_out_file: Destination of collected button sequences, in Markdown
        :param image_out_path: 
        :param md_in_file: Source of button_sequences. Only used for file-overwrite protection.
        :param button_sequences: 
        :param opt: 
        :return: 
        """
        validate_files(md_in_file, md_out_file)

        # TODO Read category_pattern_file, replacing self.categories with local
        categories = self.load_categories(category_pattern_file)

        if not button_sequences:
            if DEBUG_LOG_SEQS:
                print("Not writing sequences Markdown, no data")
            return

        with open(file=md_out_file, mode="w") as fout:
            with MarkdownRenderer() as renderer:
                print("Formatting sequences to tables ...")
                labels = categories[LABEL_VALUE]
                sections = categories[SECTION_VALUE]
                self.render_to_file(fout, renderer, button_sequences, image_out_path, opt, labels, sections)

    @staticmethod
    def render_to_file(fout, renderer, button_sequences, image_out_path, opt: ImageOpt,
                       category_labels, category_sections):
        """Derive category from description text, mapping keywords to known categories, using the best match."""
        # TODO 
        # TODO Create columns 
        # TODO Create tables
        ButtonSequence.init_description(button_sequences, renderer)

        # all_categories = set()  # Track unique categories across sentences
        # category_counts = {}  # Count occurrences of each category
        doc = Document("")
        failure_count = 0

        sections: [Section] = []

        unpacked_labels = [{item.name: item.keywords} for item in category_labels]
        unpacked_sections = [{item.name: item.keywords} for item in category_sections]
        section = None

        # Map seqs to their categories
        for seq, next_seq in pairwise(button_sequences):
            found_label_names = find_category_names(seq.description, unpacked_labels)
            found_section_names = find_category_names(seq.section, unpacked_sections)

            if not len(found_label_names) or not len(found_section_names):
                print(f"Failed to find category (label or section) for '{seq.description_printable()}'",
                      file=sys.stderr)

                failure_count += 1
                continue
            elif len(found_section_names) > 1:
                print(
                    f"Guessing section, unexpectedly found multiple sections for "
                    f"'{seq.description_printable()}': {found_section_names}")
                pass
                # # Count stuff
                # all_found_names.update(found_names)
                # 
                # for name in found_names:
                #     name_counts[name] = name_counts.get(name, 0) + 1

            # TODO Decide on a category for each line
            combo = Combo(seq, found_label_names)

            # Add to the current section
            if not section:
                section_name = found_section_names[0]

                # Reuse existing section
                found_section = WriteSequences.find_section_by_name(section_name, sections)
                if found_section:
                    section = found_section
                else:
                    section = Section(section_name, combos=[combo])
                    sections.append(section)
            else:
                section.combos.append(combo)

            # Prepare for next iteration, handle found next section
            if seq.section is not next_seq.section:
                section = None

            #     # Dump the accumulated table data: headings and fields
            # 
            #     all_categories, category_counts = set(), {}

            # all_categories, category_counts = (
            #     WriteSequences.handle_next_seq(all_categories, category_counts, doc, seq, next_seq))

            # TODO Dump all the categories at once, zipping them together
        # found_categories, failure_count = (
        #     WriteSequences.handle_current_seq(all_categories, category_counts, failure_count,
        #                                       seq, unpacked_labels))

        # WriteSequences.write_table(all_categories, category_counts, doc)
        # WriteSequences.print_next_section_title(doc, next_seq.section)

        # WriteSequences.print_next_section_title(doc, button_sequences[0].section)
        # 
        # for seq, next_seq in pairwise(button_sequences):
        #     failure_count = (
        #         WriteSequences.handle_current_seq(all_categories, category_counts, failure_count,
        #                                           seq, category_keywords))
        # 
        #     all_categories, category_counts = (
        #         WriteSequences.handle_next_seq(all_categories, category_counts, doc, seq, next_seq))

        # Build output

        for section in sections:
            WriteSequences.print_next_section_title(doc, section.name)

            # Collect Categories to be used
            column_headings = [c.found_categories[0] for c in section.combos]
            unique_column_headings = list(set(column_headings))

            headers = WriteSequences.to_table_line(unique_column_headings)
            header_aligns = WriteSequences.to_table_line(["--"], len(unique_column_headings))
            header_text = headers + header_aligns

            # TODO organize into columns
            # TODO iterate over all columns in step
            
            rows = []
            combo:Combo
            for combo in section.combos:
                rows.append(f"{combo.seq.text}<br>{combo.seq.md_image_link(image_out_path, opt)}"
                            f"<br>{combo.seq.description}")
            # columns = ["SHIFT + B1 <br> ![label-1.1](link-1.1) <br> Cell 1.1 text",
            #            "SHIFT + B2 <br> ![label-2.1](link-2.1) <br> Cell 2.1 text",
            #            "SHIFT + B3 <br> ![label-3.1](link-3.1) <br> Cell 3.1 text"]
            # rows = [columns[0],
            #         "SHIFT + B1 <br> ![label-1.2](link-1.2) <br> Cell 1.2 text",
            #         "SHIFT + B1 <br> ![label-1.3](link-1.3) <br> Cell 1.3 text"]
            row_text = WriteSequences.to_table_line(rows)
            table_text = header_text + row_text

            doc.children.append(WriteSequences.create_table(table_text))

        if failure_count:
            print(f"Failed to find category for {failure_count} sequences.", file=sys.stderr)

        print("rendering ...")
        md = renderer.render(doc)
        fout.write(md)

    @staticmethod
    def find_section_by_name(section_name, sections):
        return next((s for s in sections if s.name == section_name), None)

    @staticmethod
    def create_title_list(text, line_number=1):
        return [WriteSequences.create_blankline(line_number),
                WriteSequences.create_paragraph(text, line_number),
                WriteSequences.create_blankline()]

    @staticmethod
    def create_table(table_text):
        table = Table((table_text, 1))
        # TRICKY: line_number is required and is not set in the constructor, only in block_token.tokenize()
        table.line_number = 1
        return table

    @staticmethod
    def create_paragraph(text, line_number=1) -> [Token]:
        lines = [text + " \n"]
        result = Paragraph(lines)
        # TRICKY: line_number is required and is not set in the constructor, only in block_token.tokenize()
        result.line_number = line_number
        return result

    @staticmethod
    def create_blankline(line_number=1):
        result = BlankLine([""])
        # TRICKY: line_number is required and is not set in the constructor, only in block_token.tokenize()
        result.line_number = line_number
        return result

    @staticmethod
    def print_next_section_title(doc: Document, title):
        if DEBUG_LOG_SEQS:
            print(f"Section '{title}'", file=sys.stderr)

        doc.children.extend(WriteSequences.create_title_list(title))

    @staticmethod
    def to_table_line(elements: [str], column_count=0) -> [str]:
        cc = 1 if not column_count else column_count
        return ["|".join(elements * cc) + "\n"]

    def load_categories(self, csv_file) -> {str: [SequenceCategory]}:
        """ Loads CSV of sequence categorization data. Changes the keywords to lower case.
        
        CSV columns:
        1. "label_or_section": Whether this is a label or section: '__label__', '__section__'.
        2. "name": Name of the category, a string.
        3. "keyword_1, keyword_2, ...": A series of columns of keywords, or key phrases. 

        :return: Dictionary of category hierarchy level to ordered lists of SequenceCategory objects.
        """
        results = {SECTION_VALUE: [], LABEL_VALUE: []}

        with open(csv_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile, skipinitialspace=True)

            # Prepare to extract keywords from numbered columns
            keyword_suffixes = [str(n) for n in range(1, KEYWORD_N_KEY_COUNT)]
            keyword_columns = [KEYWORD_N_PREFIX_KEY + suffix for suffix in keyword_suffixes]

            for row in reader:
                row: dict  # Workaround for https://youtrack.jetbrains.com/issue/PY-60440

                is_section = row[LABEL_OR_SECTION_CSV_HEADER] == SECTION_KEY
                if not is_section and row[LABEL_OR_SECTION_CSV_HEADER] != LABEL_KEY:
                    # Ignore comments
                    if not row[LABEL_OR_SECTION_CSV_HEADER].startswith('#'):
                        print(f"Cannot parse row, unrecognized '{LABEL_OR_SECTION_CSV_HEADER}': {row}")
                    continue

                keywords = [a.lower() for a in list(filter(None, [row.get(k, None) for k in keyword_columns]))]

                category = SequenceCategory(
                    is_section=is_section,
                    name=row[NAME_KEY],
                    keywords=keywords,
                    is_default=(DEFAULT_NAME_KEY in keywords)
                )

                results[is_section].append(category)

        if DEBUG_LOG_SEQS:
            print(results, file=sys.stderr)

        return results
