<script>
    export let title = "Code Snippet";
    export let content = "";
    export let language = "python";

    let showToast = false;

    const copyToClipboard = () => {
        navigator.clipboard.writeText(content).then(() => {
            showToast = true;
            setTimeout(() => {
                showToast = false;
            }, 2000);
        }).catch((err) => {
            console.error("Failed to copy:", err);
        });
    };
</script>

<div class="bg-gray-800 rounded-lg p-4">
    <div class="flex justify-between items-center mb-3">
        <div class="text-sm text-gray-300">{title} ({language})</div>
        <button
            on:click={copyToClipboard}
            class="px-3 py-1 text-sm bg-gray-700 text-gray-300 rounded hover:bg-gray-600"
        >
            Copy
        </button>
    </div>

    <div class="bg-gray-900 rounded p-4">
        <pre class="overflow-x-auto">
            <code class="block text-sm text-white whitespace-pre font-mono">
{content}
            </code>
        </pre>
    </div>

    {#if showToast}
        <div class="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow">
            Copied to clipboard!
        </div>
    {/if}
</div>
