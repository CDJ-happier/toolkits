import os.path

from pypdf import PdfReader, PdfWriter
import argparse


def get_args():
    parser = argparse.ArgumentParser("PDF helper for split, extract, merge.")
    parser.add_argument("--input_pdf_path", type=str, default="example.pdf", help="Input PDF file path")
    parser.add_argument("--operation_type", type=str, default=None,
                        help="operation type, split (into odd and even pages) or extract(e.g., 1,3,9)")
    parser.add_argument("--start_page", type=int, default=1, help="start page no")
    parser.add_argument("--end_page", type=int, default=None, help="end page no")
    # for split pdf into two pdf files
    parser.add_argument("--odd_pages_name", type=str, default=None, help="Output PDF file name for odd pages")
    parser.add_argument("--even_pages_name", type=str, default=None, help="Output PDF file name for even pages")
    # for extract pages from pdf file
    parser.add_argument("--extract_pages_number", type=str, default=None,
                        help="Output PDF file name for extracted pages, e.g., 1,3,5")
    return parser.parse_args()


def split_pdf_odd_even(args):
    r"""
    split a pdf file into two pdf files, which are separately odd pages and even pages.
    arg that args must contain:
        input_pdf_path: e.g., D:\\CDJ\\xxx.pdf
        odd_pages_name: default set to xxx_odd.pdf in same basedir with input pdf path
        event_pages_name: default set to xxx_even.pdf in same basedir with input pdf path
    extra args:
        start page no: page number for starting split in [1, 2, ...], not zero. default set to 1.
        end page no: page number for ending split in [1, 2, ...], not zero. default set to len(pdf file).
    """
    assert args.input_pdf_path, "input_pdf_path is required."
    reader = PdfReader(args.input_pdf_path)
    base_dir = os.path.dirname(args.input_pdf_path)
    basename = os.path.basename(args.input_pdf_path)
    odd_writer = PdfWriter()
    even_writer = PdfWriter()
    odd_pages_name = args.odd_pages_name if args.odd_pages_name is not None else basename[:-4] + "_odd.pdf"
    even_pages_name = args.even_pages_name if args.even_pages_name is not None else basename[:-4] + "_even.pdf"
    odd_pages_output = os.path.join(base_dir, odd_pages_name)
    even_pages_output = os.path.join(base_dir, even_pages_name)

    start_no = args.start_page if args.start_page else 1
    end_no = args.end_page if args.end_page else len(reader.pages) + 1

    for cur_no in range(start_no, end_no):
        cur_page = reader.get_page(cur_no - 1)
        if cur_no % 2 == 1:
            odd_writer.add_page(cur_page)
        else:
            even_writer.add_page(cur_page)
    with open(odd_pages_output, "wb") as odd_file:
        odd_writer.write(odd_file)
    with open(even_pages_output, "wb") as even_file:
        even_writer.write(even_file)
    print(f"split pdf done# odd file -> {odd_pages_output}, even file -> {even_pages_output}")


def extract_pdf_pages(args):
    r"""
    extract pdf pages from args.extract_pages_number.
    example 1:
        extract pdf pages into single pdf file according to extract_pages_number, which is a string formatted in 1,3,8
        cmd: python pdf_tool.py input_file extract 1,3,4,8,9
    example 2:
        extract pdf pages from start_page to end_page and merge into one pdf file, the filename is xxx_page{s}-{e}.pdf
        cmd: python pdf_tool.py input_file extract --start_page 3 --end_page 21
    """
    assert args.input_pdf_path, "input_pdf_path is required."
    assert args.extract_pages_number or args.start_page or args.end_page,\
        "extract_pages_number or start_page or end_page is required."
    reader = PdfReader(args.input_pdf_path)
    base_dir = os.path.dirname(args.input_pdf_path)
    basename = os.path.basename(args.input_pdf_path)[:-4]
    if args.extract_pages_number:
        no_list = args.extract_pages_number.split(",")
        for no in no_list:
            no = int(no)
            if no > len(reader.pages):
                raise ValueError(f"page number {no} is out of range, max page number is {len(reader.pages)}")
            cur_page = reader.get_page(no - 1)
            cur_page_output = os.path.join(base_dir, f"{basename}_{no}.pdf")
            writer = PdfWriter()
            writer.add_page(cur_page)
            with open(cur_page_output, "wb") as cur_page_file:
                writer.write(cur_page_file)
            print(f"extract page {basename} No. {no} done# saved to >>> {cur_page_output}")
    elif args.start_page or args.end_page:
        if not args.start_page:
            args.start_page = 1
        if not args.end_page:
            args.end_page = len(reader.pages) + 1
        writer = PdfWriter()
        for cur_no in range(args.start_page, args.end_page):
            cur_page = reader.get_page(cur_no - 1)
            writer.add_page(cur_page)
        cur_page_output = os.path.join(base_dir, f"{basename}_page{args.start_page}-{args.end_page}.pdf")
        with open(cur_page_output, "wb") as cur_page_file:
            writer.write(cur_page_file)
        print(f"extract page {basename} No. {args.start_page}-{args.end_page} done# saved to >>> {cur_page_output}")


if __name__ == '__main__':
    args = get_args()
    operation_type = args.operation_type
    if operation_type == "split":
        split_pdf_odd_even(args)
    elif operation_type == "extract":
        extract_pdf_pages(args)
    else:
        raise ValueError(f"operation type {operation_type} is not supported.")
