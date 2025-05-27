# PDF Highlight Extractor

A Python tool for extracting highlighted text from PDF files with precise text ordering and intelligent hyphenation handling.

## Features

- **4-Color Support**: Extracts Yellow, Pink, Green, and Blue highlights
- **Smart Text Ordering**: Fixes PDF text extraction order issues using multiple methods
- **Hyphenation Merging**: Automatically combines hyphenated words across lines ("lin-" + "guistics" → "linguistics")
- **Precise Boundaries**: Configurable overlap detection to avoid over-extraction
- **Multiple Extraction Methods**: Fallback system for maximum compatibility
- **Cross-page Support**: Handles highlights that span multiple pages
- **Test Mode**: Quick testing with default settings
- **Export Options**: JSON and CSV output formats

## Installation

Clone the repository:
git clone <repository-url>
cd pdf-highlight-extractor

Install required packages:
pip install PyMuPDF pdfplumber colorama pandas


## Dependencies

- PyMuPDF (fitz) - PDF processing and text extraction
- pdfplumber - Additional PDF annotation support
- colorama - Colored terminal output
- pandas - CSV export functionality

## Usage

### Quick Test Mode
python highlight_extractor.py --test

Uses default file: `/mnt/c/Users/admin/Downloads/test2.pdf` and displays results only.

### Interactive Mode
python highlight_extractor.py

Prompts for PDF file path and output options.

### Command Line Flags
- `--test`, `-t`, or `test` - Enable test mode with defaults
- No flags - Full interactive mode

## Output Formats

### Terminal Display
📄 Page 35
🎨 YELLOW
"We end with some specific suggestions for what we can do as linguists"
🎨 PINK (hyphen-merged)
"linguistics itself"

### JSON Export
{
    "highlights": [
        {
            "page": 35,
            "text": "We end with some specific suggestions",
            "color": "yellow",
            "type": "highlight"
        }
    ]
}

### CSV Export
Tabular format with columns: page, text, color, type, category

## Technical Features

### Text Ordering Algorithm
1. **Method A**: PyMuPDF built-in sorting
2. **Method B**: Text block extraction with geometric sorting
3. **Method C**: Enhanced word-level sorting with line detection

### Hyphenation Detection
- Same-page: Detects hyphens within 8-30 pixel line spacing
- Cross-page: Handles hyphenation across page boundaries
- Smart merging: Only merges clear hyphenation patterns

### Precision Control
- **Overlap Threshold**: 40% word overlap required for inclusion
- **Boundary Expansion**: +2 pixel expansion for edge words
- **Line Tolerance**: 5-pixel tolerance for same-line detection

## Troubleshooting

### Common Issues

**Text Order Problems**: The tool uses multiple methods to fix PDF text ordering issues. If text still appears scrambled, the PDF may have complex layout encoding.

**Missing Words**: Lower the overlap threshold or check if highlights are too light/transparent.

**Over-extraction**: The tool is designed to avoid this, but very close text might be included. Check highlight precision in your PDF.

### Debug Output
Run with detailed logging to see extraction decisions:
python highlight_extractor.py --test

## Contributing

1. Create a feature branch from main
2. Make your changes
3. Test with sample PDFs
4. Submit a pull request

## License

MIT License

## Support

For issues or questions, please open a GitHub issue.

# PDF Highlight Extraction Process - Step by Step

## Phase 1: Initialization and Setup
1. **Script Startup**: Check command line arguments for test mode
2. **Path Resolution**: Determine PDF file path (default or user input)
3. **File Validation**: Verify PDF file exists and is accessible
4. **Object Creation**: Initialize PDFHighlightExtractor with file path

## Phase 2: PDF Analysis and Loading
1. **Document Opening**: Load PDF using PyMuPDF (fitz) library
2. **Page Iteration**: Loop through each page in the document
3. **Annotation Discovery**: Find all annotations on each page
4. **Type Filtering**: Identify highlight-type annotations specifically

## Phase 3: Color Classification
1. **Color Extraction**: Get RGB values from annotation properties
2. **Color Normalization**: Convert to 0-255 range if needed
3. **Color Mapping**: Classify into 4 categories (Yellow, Pink, Green, Blue)
4. **Unknown Filtering**: Skip annotations with unrecognized colors

## Phase 4: Text Extraction (Multi-Method Approach)

### Method A: Built-in Sorting
1. **Rectangle Expansion**: Add 2-pixel buffer around highlight area
2. **PyMuPDF Extraction**: Use page.get_text("text", sort=True)
3. **Text Cleaning**: Remove extra whitespace and normalize
4. **Success Check**: Return if valid text found

### Method B: Text Block Extraction  
1. **Block Discovery**: Get text blocks from highlight area
2. **Geometric Sorting**: Sort blocks by Y-position, then X-position
3. **Block Combination**: Join block texts with spaces
4. **Quality Check**: Verify result makes sense

### Method C: Enhanced Word Sorting
1. **Word Collection**: Get all words intersecting highlight area
2. **Overlap Calculation**: Calculate intersection ratio for each word
3. **Threshold Filtering**: Include words with 40%+ overlap
4. **Line Detection**: Group words by Y-position (5-pixel tolerance)
5. **Line Sorting**: Sort lines top-to-bottom
6. **Word Sorting**: Sort words left-to-right within each line
7. **Text Assembly**: Combine words in proper reading order

## Phase 5: Hyphenation Detection and Merging
1. **Pattern Recognition**: Look for highlights ending with '-'
2. **Proximity Check**: Verify next highlight is same color and nearby
3. **Distance Validation**: Check reasonable line spacing (8-30 pixels)
4. **Page Handling**: Support both same-page and cross-page hyphenation
5. **Text Joining**: Remove hyphen and combine words seamlessly

## Phase 6: Data Organization
1. **Highlight Storage**: Create structured data objects for each highlight
2. **Sorting**: Order by page number, then Y-position, then X-position
3. **Merging**: Apply hyphenation merging where detected
4. **Categorization**: Separate annotations from background highlights

## Phase 7: Output Generation

### Terminal Display
1. **Page Grouping**: Organize results by page number
2. **Color Coding**: Apply terminal colors for visual distinction
3. **Status Indicators**: Show merge status (hyphen-merged, cross-page)
4. **Formatting**: Clean, readable text presentation

### File Export (Optional)
1. **JSON Generation**: Structure data with metadata
2. **CSV Creation**: Tabular format for analysis
3. **File Writing**: Save to specified output paths

## Phase 8: Cleanup and Reporting
1. **Resource Cleanup**: Close PDF document properly
2. **Statistics**: Report extraction counts and timing
3. **Status Messages**: Provide user feedback on results
4. **Memory Management**: Clean up temporary objects

## Error Handling Throughout
- **Try-Catch Blocks**: Graceful handling of PDF parsing errors
- **Fallback Methods**: Alternative extraction approaches
- **Validation Checks**: Verify data integrity at each step
- **User Feedback**: Clear error messages and debugging info

## Debug Information
- **Overlap Ratios**: Show word inclusion/exclusion decisions
- **Method Success**: Indicate which extraction method worked
- **Hyphenation Detection**: Log when word merging occurs
- **Performance Timing**: Track processing duration