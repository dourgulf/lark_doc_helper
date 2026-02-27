import os
import time
import lark_oapi as lark
from lark_oapi.api.wiki.v2 import GetNodeSpaceRequest
from lark_oapi.api.docx.v1 import ListDocumentBlockRequest, GetDocumentBlockChildrenRequest, CreateDocumentBlockChildrenRequest, BatchDeleteDocumentBlockChildrenRequest, PatchDocumentBlockRequest
from lark_oapi.api.drive.v1 import DownloadMediaRequest, BatchGetTmpDownloadUrlMediaRequest

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
        Creates a table with content.
        NEW STRATEGY:
        1. Create an empty Table (Type 31).
        2. Create Rows (Type 32) containing Text Blocks (Type 2) as cells.
           This avoids the default empty block issue in Type 33 cells.
        """
        
        # 1. Create the table block
        # We assume table_block is Type 31 and has property set.
        # We ensure it has NO children in the creation call to avoid "Invalid parameter type".
        
        # Create the table block
        created_blocks = self.create_blocks(document_id, parent_id, [table_block])
        if not created_blocks:
            raise Exception("Failed to create table block")
            
        created_table = created_blocks[0]
        table_id = created_table.block_id
        
        print(f"Created Table {table_id}. Now creating {len(content_rows)} rows...")
        
        # 2. Delete any auto-generated rows (if any)
        # Usually Lark creates a 1x1 or sized table if row_size > 0.
        # But we want to append our own rows.
        # We can try to delete existing children first, OR just append ours.
        # If we append, the empty rows will remain at top.
        # So let's try to delete them.
        
        try:
            existing_children = self._fetch_block_children(document_id, table_id)
            if existing_children:
                print(f"  Deleting {len(existing_children)} auto-generated rows...")
                # We can batch delete by index.
                self.delete_block_children(document_id, table_id, 0, len(existing_children))
        except Exception as e:
            print(f"  Warning: Failed to cleanup auto-generated rows: {e}")

        # 3. Create Rows with content
        # content_rows contains Block(Type 32) with children=Block(Type 2)
        
        # We create them in batches
        try:
            self.create_blocks(document_id, table_id, content_rows)
            print(f"  Successfully created {len(content_rows)} rows with content.")
        except Exception as e:
            print(f"  Failed to create rows: {e}")
            # Fallback? No, if this fails, we are stuck.
            raise e
            
        return created_blocks
