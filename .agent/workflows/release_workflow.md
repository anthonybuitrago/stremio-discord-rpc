---
description: How to create and publish a new release on GitHub
---

This workflow guides you through the process of creating a new release for the Stremio Discord RPC application.

## Prerequisites
- Ensure you have the latest `StremioRPC.exe` built.
- Ensure you are on the `main` branch and it is up to date.

## Steps

1.  **Tag the Release**
    Since the last release was `v5.0`, we will tag this new version as `v5.1`.
    Run the following command:
    ```powershell
    git tag v5.1
    ```

2.  **Push the Tag**
    Push the tag to the remote repository:
    ```powershell
    git push origin v5.1
    ```

3.  **Create Release on GitHub**
    - Go to your repository on GitHub: https://github.com/anthonybuitrago/stremio-discord-rpc/releases
    - Click "Draft a new release".
    - Click "Choose a tag" and select `v5.1`.
    - **Title**: `v5.1 - Performance & Stability Update`
    - **Description**:
      ```markdown
      ## What's Changed
      - **Removed Pause Detection**: Fixed issues with false positives when Stremio is open but not playing.
      - **Enhanced Metadata Fetching**: Improved cover art detection and title cleaning.
      - **Code Cleanup**: Removed unused branches and optimized backend logic.
      ```
    - **Assets**: Drag and drop the `StremioRPC.exe` file.

4.  **Publish**
    - Click "Publish release".
