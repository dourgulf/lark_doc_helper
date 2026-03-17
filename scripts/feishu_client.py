import os
import time
import lark_oapi as lark
from lark_oapi.api.wiki.v2 import GetNodeSpaceRequest
from lark_oapi.api.docx.v1 import ListDocumentBlockRequest, GetDocumentBlockChildrenRequest, CreateDocumentBlockChildrenRequest, BatchDeleteDocumentBlockChildrenRequest, PatchDocumentBlockRequest
from lark_oapi.api.drive.v1 import DownloadMediaRequest, BatchGetTmpDownloadUrlMediaRequest, UploadAllMediaRequest
from lark_oapi.api.drive.v1.model import UploadAllMediaRequestBody
from lark_oapi.api.docx.v1.model import Block, Text, TextRun, TextElement, Image as DocxImage, UpdateBlockRequest, ReplaceImageRequest

class FeishuClient:
    def __init__(self, app_id, app_secret, domain=None):
        builder = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret)
            
        if domain:
            builder.domain(domain)
            
        self.client = builder.build()

    def download_media(self, file_token):
        request = DownloadMediaRequest.builder() \
            .file_token(file_token) \
            .build()
            
        response = self.client.drive.v1.media.download(request)
        
        if not response.success():
            print(f"Warning: Failed to download media {file_token}: {response.msg}")
            return None
            
        return response.file.read()

    def get_temp_download_url(self, file_token):
        request = BatchGetTmpDownloadUrlMediaRequest.builder() \
            .file_tokens(file_token) \
            .build()
            
        response = self.client.drive.v1.media.batch_get_tmp_download_url(request)
        
        if not response.success():
            print(f"Warning: Failed to get temp URL for {file_token}: {response.msg}")
            return None
            
        if response.data and response.data.tmp_download_urls:
            return response.data.tmp_download_urls[0].tmp_download_url
            
        return None

    def upload_media(self, file_path, parent_node):
        """Upload a local image to Lark Drive for embedding in a document.
        parent_node must be the block_id of an already-created Image block (type 27).
        Returns file_token or None on failure."""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            body = UploadAllMediaRequestBody.builder() \
                .file_name(file_name) \
                .parent_type("docx_image") \
                .parent_node(parent_node) \
                .size(file_size) \
                .file(f) \
                .build()
            request = UploadAllMediaRequest.builder().request_body(body).build()
            response = self.client.drive.v1.media.upload_all(request)
        if response.success():
            return response.data.file_token
        print(f"Warning: Failed to upload image '{file_name}': {response.msg}")
        return None

    @staticmethod
    def _get_image_display_size(file_path):
        """Return (width, height) of an image as it would be displayed,
        accounting for EXIF orientation in JPEG files.
        Returns (None, None) if dimensions cannot be determined."""
        import struct

        with open(file_path, "rb") as f:
            header = f.read(2)

        # ── JPEG ──────────────────────────────────────────────────────────────
        if header == b'\xff\xd8':
            raw_w, raw_h, orientation = None, None, 1
            with open(file_path, "rb") as f:
                data = f.read()

            i = 2
            while i < len(data) - 3:
                if data[i] != 0xff:
                    break
                marker = data[i + 1]
                if marker in (0xd8, 0xd9):  # SOI / EOI – no length field
                    i += 2
                    continue
                if i + 3 >= len(data):
                    break
                seg_len = struct.unpack('>H', data[i + 2:i + 4])[0]

                # APP1 → EXIF orientation
                if marker == 0xe1 and data[i + 4:i + 8] == b'Exif':
                    exif = data[i + 10:i + 2 + seg_len]
                    if len(exif) >= 8:
                        endian = '<' if exif[:2] == b'II' else '>'
                        ifd_off = struct.unpack(endian + 'I', exif[4:8])[0]
                        if ifd_off + 2 <= len(exif):
                            num = struct.unpack(endian + 'H', exif[ifd_off:ifd_off + 2])[0]
                            for k in range(num):
                                e = ifd_off + 2 + k * 12
                                if e + 12 > len(exif):
                                    break
                                tag = struct.unpack(endian + 'H', exif[e:e + 2])[0]
                                if tag == 0x0112:  # Orientation
                                    orientation = struct.unpack(endian + 'H', exif[e + 8:e + 10])[0]
                                    break

                # SOF0/SOF1/SOF2 → pixel dimensions
                elif marker in (0xc0, 0xc1, 0xc2):
                    raw_h = struct.unpack('>H', data[i + 5:i + 7])[0]
                    raw_w = struct.unpack('>H', data[i + 7:i + 9])[0]

                i += 2 + seg_len

            if raw_w is None:
                return None, None
            # Orientations 5-8 rotate 90° or 270° → swap axes
            if orientation in (5, 6, 7, 8):
                return raw_h, raw_w
            return raw_w, raw_h

        # ── PNG ───────────────────────────────────────────────────────────────
        if header == b'\x89P':
            with open(file_path, "rb") as f:
                f.read(16)  # skip PNG sig + length + "IHDR"
                w = struct.unpack('>I', f.read(4))[0]
                h = struct.unpack('>I', f.read(4))[0]
            return w, h

        return None, None

    def create_image_block(self, document_id, parent_id, file_path, index=-1):
        """Create an Image block (type 27) from a local file via 3-step process:
        1. Create an empty Image block to get a block_id.
        2. Upload the image with parent_node=block_id.
        3. Patch the block with replace_image to set the file_token and display dimensions.
        Returns the created block_id, or None on failure."""
        # Step 1: Create empty Image block
        empty_img_block = Block.builder().block_type(27).image(DocxImage()).build()
        created = self.create_blocks(document_id, parent_id, [empty_img_block], index=index)
        if not created:
            print(f"Warning: Failed to create empty Image block for '{file_path}'")
            return None
        block_id = created[0].block_id

        time.sleep(0.1)

        # Step 2: Upload image using the new block_id as parent_node
        file_token = self.upload_media(file_path, block_id)
        if not file_token:
            return None

        time.sleep(0.1)

        # Step 3: Patch block with the file_token and correct display dimensions
        w, h = self._get_image_display_size(file_path)
        img_builder = ReplaceImageRequest.builder().token(file_token)
        if w and h:
            img_builder = img_builder.width(w).height(h)
        patch_req = PatchDocumentBlockRequest.builder() \
            .document_id(document_id) \
            .block_id(block_id) \
            .request_body(UpdateBlockRequest.builder()
                .replace_image(img_builder.build())
                .build()) \
            .build()
        resp = self.client.docx.v1.document_block.patch(patch_req)
        if not resp.success():
            print(f"Warning: Failed to set image for block {block_id}: {resp.msg}")
            return None
        return block_id

    def get_wiki_node_info(self, token):
        # Retrieve wiki node info to get the actual document token and type
        request = GetNodeSpaceRequest.builder() \
            .token(token) \
            .build()
        
        response = self.client.wiki.v2.space.get_node(request)
        
        if not response.success():
            raise Exception(f"Failed to get wiki node info: {response.msg}")
            
        return response.data.node

    def _fetch_block_children(self, document_id, block_id):
        children = []
        page_token = None
        while True:
            builder = GetDocumentBlockChildrenRequest.builder() \
                .document_id(document_id) \
                .block_id(block_id) \
                .page_size(500)
            
            if page_token:
                builder.page_token(page_token)
            
            request = builder.build()
            
            response = self.client.docx.v1.document_block_children.get(request)
            
            if not response.success():
                if 'frequency' in response.msg.lower() or 'rate' in response.msg.lower() or 'limit' in response.msg.lower():
                    print(f"Warning: Rate limited fetching children for block {block_id}. Retrying in 1s...")
                    time.sleep(1)
                    continue
                print(f"Warning: Failed to get children for block {block_id}: {response.msg}")
                break
            
            if response.data.items:
                children.extend(response.data.items)
            
            page_token = response.data.page_token
            if not page_token:
                break
        return children

    def get_docx_blocks(self, document_id):
        # Fetch all blocks of a document
        blocks = []
        page_token = None
        
        while True:
            builder = ListDocumentBlockRequest.builder() \
                .document_id(document_id) \
                .page_size(500)
            
            if page_token:
                builder.page_token(page_token)
            
            request = builder.build()
            
            response = self.client.docx.v1.document_block.list(request)
            
            if not response.success():
                raise Exception(f"Failed to get document blocks: {response.msg}")

            if response.data.items:
                blocks.extend(response.data.items)
            
            page_token = response.data.page_token
            if not page_token:
                break

        # Check for missing content in table cells
        # We need to iteratively fetch missing content because the hierarchy is deep:
        # Table (31) -> Row (32) -> Cell (33) -> Content (2, etc.)
        # ListDocumentBlockRequest might return Table and Rows, but not Cells, or Cells but not Content.
        
        processed_ids = set()
        
        # Max 3 passes to handle depth
        for pass_index in range(3):
            # Re-build parent map from current blocks
            parent_map = {}
            for b in blocks:
                pid = b.parent_id
                if pid not in parent_map:
                    parent_map[pid] = []
                parent_map[pid].append(b)
            
            missing_content_blocks = []
            
            for b in blocks:
                # Table Row (32) should have children (Cells 33)
                if b.block_type == 32: 
                    children = parent_map.get(b.block_id, [])
                    if not children:
                        if b.block_id not in processed_ids:
                            missing_content_blocks.append(b.block_id)

                # Table Cell (33) should have children (Content)
                elif b.block_type == 33: 
                    children = parent_map.get(b.block_id, [])
                    if not children:
                        if b.block_id not in processed_ids:
                            missing_content_blocks.append(b.block_id)
                            
            if not missing_content_blocks:
                break
                
            # Remove duplicates
            missing_content_blocks = list(set(missing_content_blocks))
            print(f"Pass {pass_index + 1}: Found {len(missing_content_blocks)} blocks (Rows/Cells) with potentially missing content. Fetching children...")
            
            fetched_count = 0
            # Use a set to track existing block IDs to avoid duplicates
            existing_ids = {b.block_id for b in blocks}
            
            for block_id in missing_content_blocks:
                processed_ids.add(block_id)
                children = self._fetch_block_children(document_id, block_id)
                if children:
                    new_children = [c for c in children if c.block_id not in existing_ids]
                    if new_children:
                        blocks.extend(new_children)
                        for c in new_children:
                            existing_ids.add(c.block_id)
                        fetched_count += 1
                # Add delay to avoid rate limiting (QPS limit)
                time.sleep(0.1) 
            print(f"Successfully fetched content for {fetched_count} blocks.")
            
            if fetched_count == 0:
                break
            
        return blocks

    def create_blocks(self, document_id, parent_id, children, index=-1):
        """
        Create blocks in a document.
        :param document_id: The document ID
        :param parent_id: The parent block ID (can be document_id for root)
        :param children: List of Block objects (or dicts representing blocks)
        :param index: Insertion index (-1 for append)
        """
        BATCH_SIZE = 50
        all_created_children = []
        
        # Calculate start index if not appending
        current_index = index
        
        for i in range(0, len(children), BATCH_SIZE):
            batch = children[i:i + BATCH_SIZE]
            
            # If we are inserting at a specific position, we need to adjust the index for subsequent batches
            # If index is -1 (append), we keep it as -1
            batch_index = -1
            if index != -1:
                batch_index = current_index
                
            request = CreateDocumentBlockChildrenRequest.builder() \
                .document_id(document_id) \
                .block_id(parent_id) \
                .request_body(lark.api.docx.v1.CreateDocumentBlockChildrenRequestBody.builder()
                    .children(batch)
                    .index(batch_index)
                    .build()) \
                .build()
            
            try:
                response = self.client.docx.v1.document_block_children.create(request)
            except Exception as e:
                print(f"Error creating blocks: {e}")
                # Retry once
                time.sleep(1)
                try:
                    response = self.client.docx.v1.document_block_children.create(request)
                except Exception as retry_e:
                    raise Exception(f"Failed to create blocks (batch {i//BATCH_SIZE + 1}) after retry: {retry_e}")
            
            if not response.success():
                # If validation failed, try to print more details if available
                print(f"Error Code: {response.code}")
                print(f"Error Msg: {response.msg}")
                if response.error:
                    print(f"Error Details: {response.error}")
                
                raise Exception(f"Failed to create blocks (batch {i//BATCH_SIZE + 1}): {response.msg}")
            
            if response.data and response.data.children:
                all_created_children.extend(response.data.children)
            
            # Update index for next batch if we are not appending
            if index != -1:
                current_index += len(batch)

            # Add a small delay to be nice to the API
            time.sleep(0.1)
            
        return all_created_children

    def delete_block_children(self, document_id, block_id, start_index=0, end_index=None):
        """
        Delete children of a block using Batch Delete (by index range) or Delete (by ID).
        The SDK BatchDeleteDocumentBlockChildrenRequest takes start_index/end_index.
        """
        request = BatchDeleteDocumentBlockChildrenRequest.builder() \
            .document_id(document_id) \
            .block_id(block_id) \
            .request_body(lark.api.docx.v1.BatchDeleteDocumentBlockChildrenRequestBody.builder()
                .start_index(start_index)
                .end_index(end_index if end_index is not None else 10) # Delete first few blocks
                .build()) \
            .build()
            
        try:
            response = self.client.docx.v1.document_block_children.batch_delete(request)
        except Exception as e:
            # If JSON decode error, it might be a success with empty body (which SDK fails to parse).
            # Lark API sometimes returns empty body for delete operations.
            if "Expecting value" in str(e):
                return True
            print(f"Warning: Exception deleting children for block {block_id}: {e}")
            return False
            
        if not response.success():
            # It's possible that there are fewer blocks than end_index, but API should handle it or error?
            # If error is "index out of range", we might need to be more careful.
            # But usually for cleanup, we just want to clear.
            print(f"Warning: Failed to delete children for block {block_id}: {response.msg}")
            return False
            
        return True

    def delete_block_children_by_ids(self, document_id, block_ids):
        """
        Delete specific child blocks by ID.
        Uses DeleteDocumentBlockChildrenRequest which takes a list of IDs.
        Wait, DeleteDocumentBlockChildrenRequest takes ONE block_id in path and 'children_ids' in body?
        Let's check API.
        
        API: DELETE /open-apis/docx/v1/documents/:document_id/blocks/:block_id/children/batch_delete
        Body: start_index, end_index
        
        There is NO batch delete by ID for children of a block in one call easily?
        
        There is `DeleteDocumentBlockRequest` (delete a block itself).
        DELETE /open-apis/docx/v1/documents/:document_id/blocks/:block_id
        
        But we want to delete children OF a cell.
        If we know the IDs of the children, we can use `DeleteDocumentBlockRequest` on each child?
        Or maybe `BatchDeleteDocumentBlockRequest` doesn't exist?
        
        Wait, I saw `BatchDeleteDocumentBlockChildrenRequest` above. It uses index.
        
        If we want to delete by ID, we might have to call Delete for each block.
        But that's slow.
        
        However, for our use case (cleaning up empty default block), we know it's at index 0.
        So we can use `delete_block_children` with start_index=0, end_index=1.
        BUT, we insert our new content first.
        If we insert at index 0, our new content becomes index 0. The old empty block becomes index 1.
        So we should delete index 1?
        
        Or, we append (index=-1). New content is at index 1. Old empty block is at index 0.
        So we delete index 0.
        
        Let's assume we append new content.
        Original: [EmptyBlock]
        Append: [EmptyBlock, NewContent...]
        We want to delete [EmptyBlock] which is index 0.
        
        So `delete_block_children(doc_id, cell_id, start_index=0, end_index=1)` should work.
        """
        pass

    def create_table(self, document_id, parent_id, table_block, content_rows):
        """
        Creates a table and then populates it with content.
        This is a workaround because creating a deep table structure (Table->Rows->Cells->Content)
        in a single call fails with validation errors.
        """
        # 1. Create the table frame (without children, but with row_size/col_size)
        # We assume table_block already has children removed or we remove them here just in case.
        # But table_block is a Block object.
        
        # We need to make sure we don't send children.
        # But SDK Block object doesn't have a way to unset children easily if built?
        # Actually, we modified markdown_to_lark.py to NOT add children.
        
        # Create the table block
        created_blocks = self.create_blocks(document_id, parent_id, [table_block])
        if not created_blocks:
            raise Exception("Failed to create table block")
            
        created_table = created_blocks[0]
        table_id = created_table.block_id
        
        print(f"Created Table {table_id}. Now populating content...")
        
        # 2. Fetch the created structure (Rows and Cells)
        # We need to get the rows first.
        try:
            rows = self._fetch_block_children(document_id, table_id)
        except Exception as e:
             # Retry fetch
             print(f"Error fetching table rows: {e}. Retrying...")
             time.sleep(1)
             rows = self._fetch_block_children(document_id, table_id)
        
        # Strategy: Flatten both source content and target structure to match cells linearly.
        # This handles cases where Lark API creates a different structure (e.g. 8x1 instead of 4x2)
        # but total cell count is consistent.
        
        # Flatten target cells
        all_target_cells = []
        for row in rows:
            # Fetch cells for this row
            cells = self._fetch_block_children(document_id, row.block_id)
            all_target_cells.extend(cells)
            
        # Flatten source content cells
        all_content_cells = []
        for content_row in content_rows:
            all_content_cells.extend(content_row.children)
            
        print(f"Table Population: Found {len(all_target_cells)} target cells and {len(all_content_cells)} content cells.")
        
        if len(all_target_cells) != len(all_content_cells):
             print(f"Warning: Cell count mismatch! Target: {len(all_target_cells)}, Content: {len(all_content_cells)}")
        
        # Fill cells
        for i, target_cell in enumerate(all_target_cells):
            if i >= len(all_content_cells):
                break

            content_cell = all_content_cells[i]
            cell_content_blocks = content_cell.children

            if not cell_content_blocks:
                continue

            print(f"  Filling Cell {i} ({target_cell.block_id}) with {len(cell_content_blocks)} block(s).")

            insert_idx = 0
            for content_block in cell_content_blocks:
                if hasattr(content_block, '_local_image_path'):
                    abs_path = content_block._local_image_path
                    alt_text = getattr(content_block, '_image_alt', os.path.basename(abs_path))
                    try:
                        if os.path.exists(abs_path):
                            self.create_image_block(document_id, target_cell.block_id, abs_path, index=insert_idx)
                            insert_idx += 1
                        else:
                            raise FileNotFoundError(f"Image not found: {abs_path}")
                    except Exception as e:
                        print(f"    Image block failed ({e}), using alt text.")
                        text_elem = TextElement.builder().text_run(
                            TextRun.builder().content(alt_text).build()
                        ).build()
                        fallback = Block.builder().block_type(2).text(
                            Text.builder().elements([text_elem]).build()
                        ).build()
                        try:
                            self.create_blocks(document_id, target_cell.block_id, [fallback], index=insert_idx)
                            insert_idx += 1
                        except Exception as e2:
                            print(f"    Fallback also failed: {e2}")
                else:
                    try:
                        self.create_blocks(document_id, target_cell.block_id, [content_block], index=insert_idx)
                        insert_idx += 1
                    except Exception as e:
                        print(f"    Failed to insert block in cell {target_cell.block_id}: {e}")

                time.sleep(0.1)
                    
        return created_blocks
