import os
import time
import lark_oapi as lark
from lark_oapi.api.wiki.v2 import GetNodeSpaceRequest
from lark_oapi.api.docx.v1 import ListDocumentBlockRequest, GetDocumentBlockChildrenRequest, CreateDocumentBlockChildrenRequest
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
        parent_map = {}
        for b in blocks:
            pid = b.parent_id
            if pid not in parent_map:
                parent_map[pid] = []
            parent_map[pid].append(b)
            
        missing_content_blocks = []
        
        # 1. Check Table Rows (Type 32) - they should contain Table Cells (Type 33)
        for b in blocks:
            if b.block_type == 32: # Table Row
                children = parent_map.get(b.block_id, [])
                # If no children, or children are not cells (this implies missing intermediate cell blocks)
                # Actually, if children are NOT Type 33, we definitely need to re-fetch to see if we missed the Cell wrapper
                # But wait, if the API returns Text block with parent_id = Row_ID, then the Cell wrapper IS missing.
                # Re-fetching children of Row might return the same thing if the API structure is weird.
                # However, usually Table Row -> Table Cell.
                if not children or any(child.block_type != 33 for child in children):
                    missing_content_blocks.append(b.block_id)

        # 2. Check Table Cells (Type 33) - they should contain content
        for b in blocks:
            if b.block_type == 33: # Table Cell
                if b.block_id not in parent_map:
                    missing_content_blocks.append(b.block_id)

        if missing_content_blocks:
            # Remove duplicates
            missing_content_blocks = list(set(missing_content_blocks))
            print(f"Found {len(missing_content_blocks)} blocks (Rows/Cells) with potentially missing content. Fetching children...")
            fetched_count = 0
            
            # Use a set to track existing block IDs to avoid duplicates
            existing_ids = {b.block_id for b in blocks}
            
            for block_id in missing_content_blocks:
                children = self._fetch_block_children(document_id, block_id)
                if children:
                    new_children = [c for c in children if c.block_id not in existing_ids]
                    if new_children:
                        blocks.extend(new_children)
                        for c in new_children:
                            existing_ids.add(c.block_id)
                        fetched_count += 1
                # Add delay to avoid rate limiting (QPS limit)
                time.sleep(0.2)
            print(f"Successfully fetched content for {fetched_count} blocks.")
            
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
            
            response = self.client.docx.v1.document_block_children.create(request)
            
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
