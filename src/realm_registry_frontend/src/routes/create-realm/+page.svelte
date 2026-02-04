<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { _, locale } from 'svelte-i18n';
  import { CONFIG } from '$lib/config.js';
  import extensionsConfig from '$lib/extensions-config.json';
  import codicesConfig from '$lib/codices-config.json';

  // Auth state
  let isLoggedIn = false;
  let userPrincipal = null;
  let authLoading = true;
  let userCredits = 0;
  const REQUIRED_CREDITS = 5;

  // Deploy mode
  let deployMode = 'automatic'; // 'automatic' or 'manual'
  
  // Automatic deployment state
  let isDeploying = false;
  let deployError = null;
  let deploySuccess = null;
  let deploymentId = null;

  onMount(async () => {
    if (browser) {
      try {
        const { isAuthenticated, getPrincipal } = await import("$lib/auth");
        isLoggedIn = await isAuthenticated();
        if (isLoggedIn) {
          userPrincipal = await getPrincipal();
          await loadUserCredits();
        }
      } catch (e) {
        console.error('Auth check failed:', e);
      }
      authLoading = false;
    }
  });

  async function loadUserCredits() {
    if (!userPrincipal) return;
    try {
      const { backend } = await import('$lib/canisters.js');
      const result = await backend.get_credits(userPrincipal.toText());
      if ('Ok' in result) {
        userCredits = Number(result.Ok.balance);
      }
    } catch (e) {
      console.error('Failed to load credits:', e);
    }
  }

  async function handleLogin() {
    const { login, getPrincipal } = await import("$lib/auth");
    const result = await login();
    if (result.principal) {
      isLoggedIn = true;
      userPrincipal = result.principal;
      await loadUserCredits();
    }
  }

  async function handleAutomaticDeploy() {
    if (!userPrincipal || userCredits < REQUIRED_CREDITS) return;
    
    isDeploying = true;
    deployError = null;
    deploySuccess = null;
    deploymentId = null;
    
    try {
      // Prepare realm configuration from formData
      const realmConfig = {
        name: formData.name,
        descriptions: formData.descriptions,
        languages: formData.languages,
        logo: formData.logoPreview,
        welcome_image: formData.welcomeImagePreview,
        welcome_messages: formData.welcome_messages,
        token_enabled: formData.token_enabled,
        token_name: formData.token_name,
        token_symbol: formData.token_symbol,
        ckbtc_enabled: formData.ckbtc_enabled,
        land_token_enabled: formData.land_token_enabled,
        land_token_name: formData.land_token_name,
        land_token_symbol: formData.land_token_symbol,
        codex_source: formData.codex_source,
        codex_package_name: formData.codex_package_name,
        codex_url: formData.codex_url,
        extensions: formData.extensions,
        assistant: formData.assistant,
      };
      
      const CANISTER_MGMT_URL = CONFIG.canister_management_url || 'https://canister-management.realmsgos.dev';
      
      // Call canister-management service to deploy
      const response = await fetch(`${CANISTER_MGMT_URL}/api/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          principal_id: userPrincipal.toText(),
          realm_config: realmConfig,
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        deployError = data.message || data.detail || 'Deployment failed. Please try again.';
        return;
      }
      
      // Deployment started - it runs in the background
      deploySuccess = true;
      deploymentId = data.deployment_id;
      
      // Refresh credits after successful deployment
      await loadUserCredits();
      
    } catch (err) {
      console.error('Automatic deployment failed:', err);
      deployError = 'Deployment failed. Please check your connection and try again.';
    } finally {
      isDeploying = false;
    }
  }

  // Wizard steps
  const STEPS = [
    { id: 'codex', label: 'Codex' },
    { id: 'land', label: 'Land & Tokens' },
    { id: 'extensions', label: 'Extensions' },
    { id: 'data', label: 'Data' },
    { id: 'basics', label: 'Basics' },
    { id: 'branding', label: 'Branding' },
    { id: 'deploy', label: 'Deploy' }
  ];

  // Available languages with translated placeholders
  const AVAILABLE_LANGUAGES = [
    { code: 'en', name: 'English', native: 'English', descPlaceholder: "Describe your realm's vision, values, and purpose...", welcomePlaceholder: "Write a welcoming message for new citizens..." },
    { code: 'es', name: 'Spanish', native: 'Español', descPlaceholder: "Describe la visión, los valores y el propósito de tu reino...", welcomePlaceholder: "Escribe un mensaje de bienvenida para los nuevos ciudadanos..." },
    { code: 'fr', name: 'French', native: 'Français', descPlaceholder: "Décrivez la vision, les valeurs et la mission de votre royaume...", welcomePlaceholder: "Rédigez un message de bienvenue pour les nouveaux citoyens..." },
    { code: 'de', name: 'German', native: 'Deutsch', descPlaceholder: "Beschreiben Sie die Vision, Werte und den Zweck Ihres Reiches...", welcomePlaceholder: "Schreiben Sie eine Willkommensnachricht für neue Bürger..." },
    { code: 'it', name: 'Italian', native: 'Italiano', descPlaceholder: "Descrivi la visione, i valori e lo scopo del tuo regno...", welcomePlaceholder: "Scrivi un messaggio di benvenuto per i nuovi cittadini..." },
    { code: 'pt', name: 'Portuguese', native: 'Português', descPlaceholder: "Descreva a visão, os valores e o propósito do seu reino...", welcomePlaceholder: "Escreva uma mensagem de boas-vindas para os novos cidadãos..." },
    { code: 'zh', name: 'Chinese', native: '中文', descPlaceholder: "描述您领域的愿景、价值观和目标...", welcomePlaceholder: "为新公民写一条欢迎信息..." },
    { code: 'ja', name: 'Japanese', native: '日本語', descPlaceholder: "あなたの領域のビジョン、価値観、目的を説明してください...", welcomePlaceholder: "新しい市民へのウェルカムメッセージを書いてください..." },
    { code: 'ko', name: 'Korean', native: '한국어', descPlaceholder: "왕국의 비전, 가치관, 목적을 설명하세요...", welcomePlaceholder: "새로운 시민들을 위한 환영 메시지를 작성하세요..." },
    { code: 'ar', name: 'Arabic', native: 'العربية', descPlaceholder: "صف رؤية مملكتك وقيمها وهدفها...", welcomePlaceholder: "اكتب رسالة ترحيب للمواطنين الجدد..." },
    { code: 'hi', name: 'Hindi', native: 'हिन्दी', descPlaceholder: "अपने राज्य की दृष्टि, मूल्यों और उद्देश्य का वर्णन करें...", welcomePlaceholder: "नए नागरिकों के लिए स्वागत संदेश लिखें..." },
    { code: 'ru', name: 'Russian', native: 'Русский', descPlaceholder: "Опишите видение, ценности и цели вашего королевства...", welcomePlaceholder: "Напишите приветственное сообщение для новых граждан..." }
  ];

  // Available governance assistants (AI bots)
  const AVAILABLE_ASSISTANTS = [
    { 
      id: 'ashoka', 
      name: 'Ashoka', 
      description: 'An AI governance assistant inspired by the principles of Emperor Ashoka - promoting peace, ethical governance, and the welfare of all citizens.',
      avatar: '🕊️',
      features: ['Conflict resolution', 'Ethical decision support', 'Community welfare focus']
    }
  ];

  // Available extensions and categories (loaded from $lib/extensions-config.json)
  const AVAILABLE_EXTENSIONS = extensionsConfig.extensions;
  const EXTENSION_CATEGORIES = extensionsConfig.categories;

  // Available codices (loaded from $lib/codices-config.json)
  const AVAILABLE_CODICES = codicesConfig.codices;

  // Helper to get extensions by category
  function getExtensionsByCategory(categoryId) {
    return AVAILABLE_EXTENSIONS.filter(ext => ext.category === categoryId);
  }

  let currentStep = 0;
  let isSubmitting = false;
  let submitError = null;

  // Form data
  let formData = {
    name: '',
    descriptions: { en: '' }, // Language-keyed descriptions
    languages: ['en'], // Default to English
    logo: null,
    logoPreview: '',
    welcome_image: null,
    welcomeImagePreview: '',
    welcome_messages: { en: '' }, // Language-keyed welcome messages
    token_enabled: true,
    token_name: '',
    token_symbol: '',
    ckbtc_enabled: false,
    land_token_enabled: false,
    land_token_name: '',
    land_token_symbol: '',
    land_token_description: '',
    land_token_supply_cap: 10000,
    // New: Geo coordinates
    geo_file: null,
    geo_file_name: '',
    // New: Codex
    codex_source: 'package', // 'package', 'file', 'url'
    codex_package_name: '',
    codex_package_version: 'latest',
    codex_file: null,
    codex_file_name: '',
    codex_url: '',
    // New: Extensions
    extensions: AVAILABLE_EXTENSIONS.map(e => e.id),
    custom_extensions: [], // Array of { name, source: 'file'|'url', file, url }
    // New: Governance Assistant
    assistant: null, // null means no assistant, or assistant id
    // New: Realm Data (users)
    realm_data_file: null,
    realm_data_file_name: ''
  };

  // Validation
  let errors = {};

  function validateStep(step) {
    errors = {};
    
    // Step 0: Codex
    if (step === 0) {
      if (formData.codex_source === 'package' && !formData.codex_package_name.trim()) {
        errors.codex_package_name = 'Package name is required';
      }
      if (formData.codex_source === 'url' && !formData.codex_url.trim()) {
        errors.codex_url = 'URL is required';
      }
      if (formData.codex_source === 'file' && !formData.codex_file) {
        errors.codex_file = 'Please upload a codex zip file';
      }
    }
    
    // Step 1: Land & Tokens
    if (step === 1) {
      if (formData.token_enabled) {
        if (!formData.token_name.trim()) {
          errors.token_name = 'Token name is required';
        }
        if (!formData.token_symbol.trim()) {
          errors.token_symbol = 'Token symbol is required';
        } else if (formData.token_symbol.length > 10) {
          errors.token_symbol = 'Symbol must be 10 characters or less';
        }
      }
      
      if (formData.land_token_enabled) {
        if (!formData.land_token_name.trim()) {
          errors.land_token_name = 'Land token name is required';
        }
        if (!formData.land_token_symbol.trim()) {
          errors.land_token_symbol = 'Land token symbol is required';
        }
      }
    }
    
    // Step 2: Extensions - no validation needed
    // Step 3: Data - no validation needed
    
    // Step 4: Basics
    if (step === 4) {
      if (!formData.name.trim()) {
        errors.name = 'Realm name is required';
      } else if (formData.name.length < 3) {
        errors.name = 'Name must be at least 3 characters';
      }
      if (formData.languages.length === 0) {
        errors.languages = 'At least one language is required';
      }
      // Validate descriptions for each language
      for (const langCode of formData.languages) {
        const desc = formData.descriptions[langCode] || '';
        if (!desc.trim()) {
          errors[`description_${langCode}`] = 'Description is required';
        } else if (desc.length < 20) {
          errors[`description_${langCode}`] = 'Description must be at least 20 characters';
        }
      }
    }
    
    // Step 5: Branding
    if (step === 5) {
      // Validate welcome messages for each language
      for (const langCode of formData.languages) {
        const msg = formData.welcome_messages[langCode] || '';
        if (!msg.trim()) {
          errors[`welcome_message_${langCode}`] = 'Welcome message is required';
        }
      }
    }
    
    return Object.keys(errors).length === 0;
  }

  function nextStep() {
    if (validateStep(currentStep)) {
      if (currentStep < STEPS.length - 1) {
        currentStep++;
      }
    }
  }

  function prevStep() {
    if (currentStep > 0) {
      currentStep--;
    }
  }

  function goToStep(index) {
    // Only allow going back or to validated steps
    if (index < currentStep) {
      currentStep = index;
    }
  }

  function handleLogoUpload(event) {
    const file = event.target.files[0];
    if (file) {
      formData.logo = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        formData.logoPreview = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  function handleWelcomeImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
      formData.welcome_image = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        formData.welcomeImagePreview = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  }

  function handleGeoFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
      formData.geo_file = file;
      formData.geo_file_name = file.name;
    }
  }

  function handleCodexFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
      formData.codex_file = file;
      formData.codex_file_name = file.name;
    }
  }

  function toggleExtension(extId) {
    // Prevent toggling mandatory extensions
    const ext = AVAILABLE_EXTENSIONS.find(e => e.id === extId);
    if (ext?.mandatory) return;
    
    if (formData.extensions.includes(extId)) {
      formData.extensions = formData.extensions.filter(id => id !== extId);
    } else {
      formData.extensions = [...formData.extensions, extId];
    }
  }

  function addCustomExtension() {
    formData.custom_extensions = [...formData.custom_extensions, { 
      name: '', 
      source: 'url', 
      file: null, 
      file_name: '',
      url: '' 
    }];
  }

  function removeCustomExtension(index) {
    formData.custom_extensions = formData.custom_extensions.filter((_, i) => i !== index);
  }

  function handleCustomExtensionFile(event, index) {
    const file = event.target.files[0];
    if (file) {
      formData.custom_extensions[index].file = file;
      formData.custom_extensions[index].file_name = file.name;
      if (!formData.custom_extensions[index].name) {
        formData.custom_extensions[index].name = file.name.replace('.zip', '');
      }
      formData.custom_extensions = [...formData.custom_extensions];
    }
  }

  function handleRealmDataUpload(event) {
    const file = event.target.files[0];
    if (file) {
      formData.realm_data_file = file;
      formData.realm_data_file_name = file.name;
    }
  }

  function removeRealmDataFile() {
    formData.realm_data_file = null;
    formData.realm_data_file_name = '';
  }

  function copyToClipboard(text) {
    if (browser) {
      navigator.clipboard.writeText(text);
    }
  }

  function generateManifest() {
    const manifest = {
      type: 'realm',
      name: formData.name,
      languages: formData.languages,
      descriptions: formData.descriptions,
      logo: formData.logo ? formData.logo.name : 'logo.png',
      welcome_image: formData.welcome_image ? formData.welcome_image.name : 'welcome.png',
      welcome_messages: formData.welcome_messages
    };

    // Realm Token (optional)
    if (formData.token_enabled) {
      manifest.token = {
        name: formData.token_name,
        symbol: formData.token_symbol.toUpperCase()
      };
    }

    // ckBTC Support
    if (formData.ckbtc_enabled) {
      manifest.ckbtc_enabled = true;
    }

    if (formData.land_token_enabled) {
      manifest.land_token = {
        name: formData.land_token_name,
        symbol: formData.land_token_symbol.toUpperCase(),
        description: formData.land_token_description || `Land ownership NFT for ${formData.name} realm`,
        supply_cap: formData.land_token_supply_cap
      };
      
      if (formData.geo_file) {
        manifest.land_token.geo_file = formData.geo_file_name;
      }
    }

    // Codex configuration
    if (formData.codex_source === 'package') {
      manifest.codex = {
        package: {
          name: formData.codex_package_name,
          version: formData.codex_package_version || 'latest'
        }
      };
    } else if (formData.codex_source === 'url') {
      manifest.codex = {
        url: formData.codex_url
      };
    } else if (formData.codex_source === 'file') {
      manifest.codex = {
        file: formData.codex_file_name
      };
    }

    // Extensions
    if (formData.extensions.length > 0 || formData.custom_extensions.length > 0) {
      manifest.extensions = {
        enabled: formData.extensions,
        custom: formData.custom_extensions.map(ext => ({
          name: ext.name,
          source: ext.source === 'url' ? ext.url : ext.file_name
        })).filter(ext => ext.name && ext.source)
      };
    }

    // Governance Assistant
    if (formData.assistant) {
      manifest.assistant = formData.assistant;
    }

    // Realm Data
    if (formData.realm_data_file) {
      manifest.realm_data = formData.realm_data_file_name;
    }

    return manifest;
  }

  async function handleSubmit() {
    if (!validateStep(currentStep)) return;
    
    isSubmitting = true;
    submitError = null;

    try {
      const manifest = generateManifest();
      
      // For now, download the manifest as a file
      // In the future, this could directly deploy via the backend
      const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'manifest.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      // Show success (no redirect, stay on deploy page)
      // User can use the downloaded manifest with the CLI
    } catch (err) {
      submitError = err.message || 'Failed to create realm';
    } finally {
      isSubmitting = false;
    }
  }

  // Auto-generate token symbol from name
  $: if (formData.name && !formData.token_symbol) {
    formData.token_symbol = formData.name.substring(0, 4).toUpperCase();
  }

  // Auto-generate land token name/symbol
  $: if (formData.land_token_enabled && formData.name) {
    if (!formData.land_token_name) {
      formData.land_token_name = `${formData.name} Land`;
    }
    if (!formData.land_token_symbol) {
      formData.land_token_symbol = `${formData.name.substring(0, 3).toUpperCase()}LAND`;
    }
  }
</script>

<svelte:head>
  <title>Create Realm | Realms</title>
</svelte:head>

<div class="wizard-container">
  <header class="wizard-header">
    <h1>Create Your Realm</h1>
    <p class="subtitle">Configure your realm settings step by step</p>
  </header>

  <!-- Progress Steps -->
  <div class="steps-container">
    <div class="steps">
      {#each STEPS as step, index}
        <button 
          class="step" 
          class:active={currentStep === index}
          class:completed={currentStep > index}
          on:click={() => goToStep(index)}
          disabled={index > currentStep}
        >
          <div class="step-number">
            {#if currentStep > index}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            {:else}
              {index + 1}
            {/if}
          </div>
          <span class="step-label">{step.label}</span>
        </button>
        {#if index < STEPS.length - 1}
          <div class="step-connector" class:completed={currentStep > index}></div>
        {/if}
      {/each}
    </div>
  </div>

  <!-- Navigation Buttons (at top) -->
  <div class="wizard-nav wizard-nav-top">
    {#if currentStep > 0}
      <button class="btn btn-secondary" on:click={prevStep}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        Back
      </button>
    {:else}
      <div></div>
    {/if}

    {#if currentStep < STEPS.length - 1}
      <button class="btn btn-primary" on:click={nextStep}>
        Continue
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
      </button>
    {:else}
      <div></div>
    {/if}
  </div>

  <!-- Form Content -->
  <div class="form-container">
    {#if currentStep === 4}
      <!-- Step 5: Basics -->
      <div class="form-step">
        <h2>Basic Information</h2>
        <p class="step-description">Give your realm a unique identity</p>

        <div class="form-group">
          <label for="name">Realm Name <span class="required">*</span></label>
          <input 
            type="text" 
            id="name" 
            bind:value={formData.name}
            placeholder="e.g., Atlantis, New Eden, Arcadia"
            class:error={errors.name}
          />
          {#if errors.name}
            <span class="error-message">{errors.name}</span>
          {/if}
        </div>

        <div class="form-group">
          <label>Supported Languages <span class="required">*</span></label>
          <p class="hint" style="margin-bottom: 0.75rem;">Select which languages your realm will support</p>
          <div class="language-grid">
            {#each AVAILABLE_LANGUAGES as lang}
              <button 
                type="button"
                class="language-chip" 
                class:selected={formData.languages.includes(lang.code)}
                on:click={() => {
                  if (formData.languages.includes(lang.code)) {
                    if (formData.languages.length > 1) {
                      formData.languages = formData.languages.filter(l => l !== lang.code);
                      delete formData.descriptions[lang.code];
                      delete formData.welcome_messages[lang.code];
                    }
                  } else {
                    formData.languages = [...formData.languages, lang.code];
                    formData.descriptions[lang.code] = '';
                    formData.welcome_messages[lang.code] = '';
                  }
                }}
              >
                <span class="lang-code">{lang.code.toUpperCase()}</span>
                <span class="lang-name">{lang.name} ({lang.native})</span>
                {#if formData.languages.includes(lang.code)}
                  <span class="lang-check">✓</span>
                {/if}
              </button>
            {/each}
          </div>
          {#if errors.languages}
            <span class="error-message">{errors.languages}</span>
          {/if}
        </div>

        <div class="form-group">
          <label>Description <span class="required">*</span></label>
          {#if formData.languages.length > 1}
            <p class="hint" style="margin-bottom: 0.75rem;">Enter description in each supported language</p>
          {/if}
          <div class="multilang-inputs">
            {#each formData.languages as langCode}
              {@const lang = AVAILABLE_LANGUAGES.find(l => l.code === langCode)}
              <div class="multilang-input">
                {#if formData.languages.length > 1}
                  <div class="multilang-label">
                    <span class="lang-code-small">{lang?.code.toUpperCase()}</span>
                    <span>{lang?.name}</span>
                  </div>
                {/if}
                <textarea 
                  id="description_{langCode}" 
                  bind:value={formData.descriptions[langCode]}
                  placeholder={lang?.descPlaceholder || "Describe your realm's vision, values, and purpose..."}
                  rows="3"
                  class:error={errors[`description_${langCode}`]}
                ></textarea>
                {#if errors[`description_${langCode}`]}
                  <span class="error-message">{errors[`description_${langCode}`]}</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>

    {:else if currentStep === 5}
      <!-- Step 6: Branding -->
      <div class="form-step">
        <h2>Branding & Welcome</h2>
        <p class="step-description">Customize how your realm looks and feels</p>

        <div class="form-row">
          <div class="form-group">
            <label>Logo</label>
            <div class="upload-area" class:has-preview={formData.logoPreview}>
              {#if formData.logoPreview}
                <img src={formData.logoPreview} alt="Logo preview" class="preview-image" />
                <button class="remove-btn" on:click={() => { formData.logo = null; formData.logoPreview = ''; }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              {:else}
                <input type="file" accept="image/*" on:change={handleLogoUpload} />
                <div class="upload-placeholder">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                  </svg>
                  <span>Upload Logo</span>
                  <span class="hint">PNG or JPG, max 2MB</span>
                </div>
              {/if}
            </div>
          </div>

          <div class="form-group">
            <label>Welcome Image</label>
            <div class="upload-area welcome-upload" class:has-preview={formData.welcomeImagePreview}>
              {#if formData.welcomeImagePreview}
                <img src={formData.welcomeImagePreview} alt="Welcome image preview" class="preview-image" />
                <button class="remove-btn" on:click={() => { formData.welcome_image = null; formData.welcomeImagePreview = ''; }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              {:else}
                <input type="file" accept="image/*" on:change={handleWelcomeImageUpload} />
                <div class="upload-placeholder">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                  </svg>
                  <span>Upload Welcome Image</span>
                  <span class="hint">Recommended: 1920x1080</span>
                </div>
              {/if}
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>Welcome Message <span class="required">*</span></label>
          {#if formData.languages.length > 1}
            <p class="hint" style="margin-bottom: 0.75rem;">Enter welcome message in each supported language</p>
          {/if}
          <div class="multilang-inputs">
            {#each formData.languages as langCode}
              {@const lang = AVAILABLE_LANGUAGES.find(l => l.code === langCode)}
              <div class="multilang-input">
                {#if formData.languages.length > 1}
                  <div class="multilang-label">
                    <span class="lang-code-small">{lang?.code.toUpperCase()}</span>
                    <span>{lang?.name}</span>
                  </div>
                {/if}
                <textarea 
                  id="welcome_message_{langCode}" 
                  bind:value={formData.welcome_messages[langCode]}
                  placeholder={lang?.welcomePlaceholder || "Write a welcoming message for new citizens..."}
                  rows="3"
                  class:error={errors[`welcome_message_${langCode}`]}
                ></textarea>
                {#if errors[`welcome_message_${langCode}`]}
                  <span class="error-message">{errors[`welcome_message_${langCode}`]}</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>

    {:else if currentStep === 1}
      <!-- Step 2: Land & Tokens -->
      <div class="form-step">
        <h2>Token Configuration</h2>
        <p class="step-description">Configure the tokens for your realm</p>

        <!-- Realm Token Section -->
        <div class="token-section">
          <div class="form-group">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={formData.token_enabled} />
              <span class="toggle-switch"></span>
              <span>Create Realm Token</span>
            </label>
            <p class="hint">Create a native token for governance and transactions within your realm</p>
          </div>

          {#if formData.token_enabled}
            <div class="token-config">
              <div class="form-row">
                <div class="form-group">
                  <label for="token_name">Token Name <span class="required">*</span></label>
                  <input 
                    type="text" 
                    id="token_name" 
                    bind:value={formData.token_name}
                    placeholder="e.g., Atlantis Token"
                    class:error={errors.token_name}
                  />
                  {#if errors.token_name}
                    <span class="error-message">{errors.token_name}</span>
                  {/if}
                </div>

                <div class="form-group">
                  <label for="token_symbol">Token Symbol <span class="required">*</span></label>
                  <input 
                    type="text" 
                    id="token_symbol" 
                    bind:value={formData.token_symbol}
                    placeholder="e.g., ATL"
                    maxlength="10"
                    class:error={errors.token_symbol}
                  />
                  {#if errors.token_symbol}
                    <span class="error-message">{errors.token_symbol}</span>
                  {/if}
                </div>
              </div>
            </div>
          {/if}
        </div>

        <div class="divider"></div>

        <!-- ckBTC Support Section -->
        <div class="token-section">
          <div class="form-group">
            <label class="toggle-label">
              <input type="checkbox" bind:checked={formData.ckbtc_enabled} />
              <span class="toggle-switch"></span>
              <span>Enable ckBTC Support</span>
            </label>
            <p class="hint">Allow users to use ckBTC (Chain-Key Bitcoin) within your realm</p>
          </div>
        </div>

        <div class="divider"></div>

        <div class="form-group">
          <label class="toggle-label">
            <input type="checkbox" bind:checked={formData.land_token_enabled} />
            <span class="toggle-switch"></span>
            <span>Enable Land Token (NFT)</span>
          </label>
          <p class="hint">Land tokens represent ownership of parcels within your realm</p>
        </div>

        {#if formData.land_token_enabled}
          <div class="land-token-config">
            <div class="form-row">
              <div class="form-group">
                <label for="land_token_name">Land Token Name <span class="required">*</span></label>
                <input 
                  type="text" 
                  id="land_token_name" 
                  bind:value={formData.land_token_name}
                  placeholder="e.g., Atlantis Land"
                  class:error={errors.land_token_name}
                />
                {#if errors.land_token_name}
                  <span class="error-message">{errors.land_token_name}</span>
                {/if}
              </div>

              <div class="form-group">
                <label for="land_token_symbol">Land Token Symbol <span class="required">*</span></label>
                <input 
                  type="text" 
                  id="land_token_symbol" 
                  bind:value={formData.land_token_symbol}
                  placeholder="e.g., ATLAND"
                  maxlength="10"
                  class:error={errors.land_token_symbol}
                />
                {#if errors.land_token_symbol}
                  <span class="error-message">{errors.land_token_symbol}</span>
                {/if}
              </div>
            </div>

            <div class="form-group">
              <label for="land_token_supply">Supply Cap</label>
              <input 
                type="number" 
                id="land_token_supply" 
                bind:value={formData.land_token_supply_cap}
                min="100"
                max="1000000"
              />
              <span class="hint">Maximum number of land parcels (100 - 1,000,000)</span>
            </div>

            <div class="divider"></div>

            <div class="form-group">
              <label for="geo_file">Geo Coordinates File</label>
              <div class="upload-area file-upload" class:has-file={formData.geo_file}>
                {#if formData.geo_file}
                  <div class="file-info">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                      <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    <span>{formData.geo_file_name}</span>
                    <button type="button" class="remove-file-btn" on:click={() => { formData.geo_file = null; formData.geo_file_name = ''; }} aria-label="Remove file">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                {:else}
                  <input type="file" accept=".json,.geojson,.csv" on:change={handleGeoFileUpload} id="geo_file_input" />
                  <div class="upload-placeholder">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                      <circle cx="12" cy="10" r="3"></circle>
                    </svg>
                    <span>Upload Geo Coordinates</span>
                    <span class="hint">GeoJSON, JSON, or CSV file</span>
                  </div>
                {/if}
              </div>
              <span class="hint">Define the geographic boundaries for land parcels</span>
            </div>
          </div>
        {/if}
      </div>

    {:else if currentStep === 0}
      <!-- Step 1: Codex -->
      <div class="form-step">
        <h2>Codex Configuration</h2>
        <p class="step-description">Configure the governance rules (Python codex files)</p>

        <div class="form-group">
          <label>Codex Source</label>
          <div class="source-tabs">
            <button 
              type="button"
              class="source-tab" 
              class:active={formData.codex_source === 'package'}
              on:click={() => formData.codex_source = 'package'}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16.5 9.4l-9-5.19M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
              Package
            </button>
            <button 
              type="button"
              class="source-tab" 
              class:active={formData.codex_source === 'url'}
              on:click={() => formData.codex_source = 'url'}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
              </svg>
              URL
            </button>
            <button 
              type="button"
              class="source-tab" 
              class:active={formData.codex_source === 'file'}
              on:click={() => formData.codex_source = 'file'}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              Upload
            </button>
          </div>
        </div>

        {#if formData.codex_source === 'package'}
          <div class="form-group">
            <label for="codex_package">Select Codex <span class="required">*</span></label>
            <div class="codex-options">
              {#each AVAILABLE_CODICES as codex}
                <button
                  type="button"
                  class="codex-card"
                  class:selected={formData.codex_package_name === codex.id}
                  on:click={() => formData.codex_package_name = codex.id}
                >
                  <div class="codex-radio">
                    {#if formData.codex_package_name === codex.id}
                      <div class="codex-radio-dot"></div>
                    {/if}
                  </div>
                  <div class="codex-info">
                    <span class="codex-name">{codex.name}</span>
                    <span class="codex-desc">{codex.description}</span>
                    {#if codex.doc_url}
                      <a href={codex.doc_url} target="_blank" rel="noopener" class="doc-link" on:click|stopPropagation>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                          <polyline points="15 3 21 3 21 9"></polyline>
                          <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                        View documentation
                      </a>
                    {/if}
                  </div>
                </button>
              {/each}
            </div>
            {#if errors.codex_package_name}
              <span class="error-message">{errors.codex_package_name}</span>
            {/if}
          </div>
          <p class="hint">Select a pre-built codex package for your realm's governance rules</p>

        {:else if formData.codex_source === 'url'}
          <div class="form-group">
            <label for="codex_url">Codex URL <span class="required">*</span></label>
            <input 
              type="text" 
              id="codex_url" 
              bind:value={formData.codex_url}
              placeholder="https://example.com/my-codex.zip"
              class:error={errors.codex_url}
            />
            {#if errors.codex_url}
              <span class="error-message">{errors.codex_url}</span>
            {/if}
            <span class="hint">URL to a zip file containing Python codex files</span>
          </div>

        {:else if formData.codex_source === 'file'}
          <div class="form-group">
            <label for="codex_file">Codex Zip File <span class="required">*</span></label>
            <div class="upload-area file-upload" class:has-file={formData.codex_file}>
              {#if formData.codex_file}
                <div class="file-info">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  <span>{formData.codex_file_name}</span>
                  <button type="button" class="remove-file-btn" on:click={() => { formData.codex_file = null; formData.codex_file_name = ''; }} aria-label="Remove file">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              {:else}
                <input type="file" accept=".zip" on:change={handleCodexFileUpload} id="codex_file_input" />
                <div class="upload-placeholder">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  <span>Upload Codex Zip</span>
                  <span class="hint">Zip file with Python codex files</span>
                </div>
              {/if}
            </div>
            {#if errors.codex_file}
              <span class="error-message">{errors.codex_file}</span>
            {/if}
          </div>
        {/if}
      </div>

    {:else if currentStep === 2}
      <!-- Step 3: Extensions -->
      <div class="form-step">
        <h2>Extensions</h2>
        <p class="step-description">Select which extensions to enable for your realm</p>

        <div class="select-all-row">
          <span class="selected-count">{formData.extensions.length} of {AVAILABLE_EXTENSIONS.length} selected</span>
          <button 
            type="button" 
            class="btn btn-small btn-outline"
            on:click={() => {
              const nonMandatory = AVAILABLE_EXTENSIONS.filter(e => !e.mandatory);
              const allSelected = nonMandatory.every(e => formData.extensions.includes(e.id));
              if (allSelected) {
                // Unselect all non-mandatory
                formData.extensions = AVAILABLE_EXTENSIONS.filter(e => e.mandatory).map(e => e.id);
              } else {
                // Select all
                formData.extensions = AVAILABLE_EXTENSIONS.map(e => e.id);
              }
            }}
          >
            {#if AVAILABLE_EXTENSIONS.filter(e => !e.mandatory).every(e => formData.extensions.includes(e.id))}
              Unselect All
            {:else}
              Select All
            {/if}
          </button>
        </div>

        {#each EXTENSION_CATEGORIES as category}
          {@const categoryExtensions = getExtensionsByCategory(category.id)}
          {#if categoryExtensions.length > 0}
            <div class="extension-category">
              <h3 class="category-title">{category.name}</h3>
              <p class="category-desc">{category.description}</p>
              <div class="extensions-grid">
                {#each categoryExtensions as ext}
                  <button 
                    type="button"
                    class="extension-card" 
                    class:selected={formData.extensions.includes(ext.id)}
                    class:mandatory={ext.mandatory}
                    on:click={() => toggleExtension(ext.id)}
                    disabled={ext.mandatory}
                  >
                    <div class="extension-check">
                      {#if formData.extensions.includes(ext.id)}
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                      {/if}
                    </div>
                    <div class="extension-info">
                      <span class="extension-name">{ext.name}{#if ext.mandatory} <span class="mandatory-badge">Required</span>{/if}</span>
                      <span class="extension-desc">{ext.description}</span>
                      {#if ext.doc_url}
                        <a href={ext.doc_url} target="_blank" rel="noopener" class="doc-link" on:click|stopPropagation>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                            <polyline points="15 3 21 3 21 9"></polyline>
                            <line x1="10" y1="14" x2="21" y2="3"></line>
                          </svg>
                          Docs
                        </a>
                      {/if}
                    </div>
                  </button>
                {/each}
              </div>
            </div>
          {/if}
        {/each}

        <div class="divider"></div>

        <div class="custom-extensions-section">
          <div class="section-header">
            <h3>Custom Extensions</h3>
            <button type="button" class="btn btn-small" on:click={addCustomExtension}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              Add Extension
            </button>
          </div>

          {#if formData.custom_extensions.length === 0}
            <p class="empty-state">No custom extensions added. Click "Add Extension" to add your own.</p>
          {:else}
            {#each formData.custom_extensions as ext, index}
              <div class="custom-extension-row">
                <div class="form-group">
                  <label for="ext_name_{index}">Name</label>
                  <input 
                    type="text" 
                    id="ext_name_{index}"
                    bind:value={ext.name}
                    placeholder="Extension name"
                  />
                </div>
                
                <div class="form-group">
                  <label>Source</label>
                  <div class="mini-tabs">
                    <button 
                      type="button"
                      class="mini-tab" 
                      class:active={ext.source === 'url'}
                      on:click={() => ext.source = 'url'}
                    >URL</button>
                    <button 
                      type="button"
                      class="mini-tab" 
                      class:active={ext.source === 'file'}
                      on:click={() => ext.source = 'file'}
                    >File</button>
                  </div>
                </div>

                {#if ext.source === 'url'}
                  <div class="form-group flex-grow">
                    <label for="ext_url_{index}">URL</label>
                    <input 
                      type="text" 
                      id="ext_url_{index}"
                      bind:value={ext.url}
                      placeholder="https://example.com/extension.zip"
                    />
                  </div>
                {:else}
                  <div class="form-group flex-grow">
                    <label for="ext_file_{index}">File</label>
                    {#if ext.file}
                      <div class="file-pill">
                        <span>{ext.file_name}</span>
                        <button type="button" on:click={() => { ext.file = null; ext.file_name = ''; }} aria-label="Remove">×</button>
                      </div>
                    {:else}
                      <input type="file" accept=".zip" on:change={(e) => handleCustomExtensionFile(e, index)} id="ext_file_{index}" />
                    {/if}
                  </div>
                {/if}

                <button type="button" class="remove-ext-btn" on:click={() => removeCustomExtension(index)} aria-label="Remove extension">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            {/each}
          {/if}
        </div>

      </div>

    {:else if currentStep === 3}
      <!-- Step 4: Data -->
      <div class="form-step">
        <h2>Realm Data</h2>
        <p class="step-description">Optionally upload initial user data for your realm</p>

        <div class="data-upload-section">
          <div class="data-info-box">
            <div class="data-info-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
            </div>
            <div class="data-info-text">
              <strong>User Data File</strong>
              <p>Upload a JSON file containing initial user records for your realm. This can include user profiles, memberships, and other user-related data.</p>
            </div>
          </div>

          {#if formData.realm_data_file}
            <div class="file-uploaded">
              <div class="file-info">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span>{formData.realm_data_file_name}</span>
              </div>
              <button type="button" class="remove-file-btn" on:click={removeRealmDataFile} aria-label="Remove file">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          {:else}
            <label class="file-upload-area">
              <input type="file" accept=".json" on:change={handleRealmDataUpload} />
              <div class="upload-content">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <span class="upload-text">Click to upload or drag and drop</span>
                <span class="upload-hint">JSON file (realm_data.json)</span>
              </div>
            </label>
          {/if}

          <p class="optional-note">This step is optional. You can add users later through your realm's admin panel.</p>
        </div>
      </div>

    {:else if currentStep === 6}
      <!-- Step 7: Deploy -->
      <div class="form-step">
        <h2>Deploy Your Realm</h2>
        <p class="step-description">Choose how you want to deploy your governance system</p>

        <div class="deploy-options">
          <!-- Option 1: Automatic Deployment -->
          <div 
            class="deploy-option" 
            class:active={deployMode === 'automatic'}
            class:disabled={!isLoggedIn || userCredits < REQUIRED_CREDITS}
            on:click={() => { if (isLoggedIn && userCredits >= REQUIRED_CREDITS) deployMode = 'automatic'; }}
            on:keydown={(e) => { if (e.key === 'Enter' && isLoggedIn && userCredits >= REQUIRED_CREDITS) deployMode = 'automatic'; }}
            role="button"
            tabindex="0"
          >
            <div class="deploy-option-header">
              <div class="deploy-option-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path>
                </svg>
              </div>
              <div>
                <h3>Automatic Deployment</h3>
                {#if !isLoggedIn}
                  <span class="badge-warning">Login Required</span>
                {:else if userCredits < REQUIRED_CREDITS}
                  <span class="badge-warning">Credits Required</span>
                {:else}
                  <span class="badge-recommended">Recommended</span>
                {/if}
              </div>
            </div>
            <p class="deploy-option-desc">Let our servers deploy and manage your realm automatically. No technical knowledge required.</p>
            
            {#if !isLoggedIn}
              <div class="deploy-requirement">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span>Please log in to use automatic deployment</span>
                <button type="button" class="btn btn-small btn-dark" on:click|stopPropagation={handleLogin}>
                  Log In
                </button>
              </div>
            {:else if userCredits < REQUIRED_CREDITS}
              <div class="deploy-requirement">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M12 6v6l4 2"></path>
                </svg>
                <span>You need at least {REQUIRED_CREDITS} credits (you have {userCredits})</span>
                <button type="button" class="btn btn-small btn-outline" on:click|stopPropagation={loadUserCredits}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path>
                    <path d="M21 3v5h-5"></path>
                  </svg>
                  Refresh
                </button>
                <a href="/my-dashboard" class="btn btn-small btn-dark" on:click|stopPropagation>
                  Buy Credits
                </a>
              </div>
            {:else if deployMode === 'automatic'}
              <!-- Deploy button when automatic mode is selected and user has credits -->
              {#if deploySuccess}
                <div class="deploy-success deploy-in-progress">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spinning">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                  </svg>
                  <div>
                    <strong>Your realm is being deployed!</strong>
                    <p class="deploy-info">Deployment typically takes 5-10 minutes. You can monitor the progress in your dashboard.</p>
                    <a href="/my-dashboard?tab=realms" class="btn btn-small btn-primary">View Deployment Status →</a>
                  </div>
                </div>
              {:else}
                <div class="deploy-action">
                  <p class="deploy-cost">Cost: <strong>{REQUIRED_CREDITS} credits</strong> (you have {userCredits})</p>
                  <button 
                    type="button" 
                    class="btn btn-primary btn-deploy" 
                    on:click|stopPropagation={handleAutomaticDeploy}
                    disabled={isDeploying}
                  >
                    {#if isDeploying}
                      <span class="spinner-small"></span>
                      Deploying...
                    {:else}
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path>
                      </svg>
                      Deploy Now
                    {/if}
                  </button>
                  {#if deployError}
                    <p class="deploy-error">{deployError}</p>
                  {/if}
                </div>
              {/if}
            {/if}
          </div>

          <!-- Option 2: Manual Deployment -->
          <div 
            class="deploy-option" 
            class:active={deployMode === 'manual'}
            on:click={() => deployMode = 'manual'}
            on:keydown={(e) => { if (e.key === 'Enter') deployMode = 'manual'; }}
            role="button"
            tabindex="0"
          >
            <div class="deploy-option-header">
              <div class="deploy-option-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="16 18 22 12 16 6"></polyline>
                  <polyline points="8 6 2 12 8 18"></polyline>
                </svg>
              </div>
              <div>
                <h3>Manual Deployment</h3>
                <span class="badge-developer">For Developers</span>
              </div>
            </div>
            <p class="deploy-option-desc">Deploy your own governance system in minutes using the CLI.</p>

            {#if deployMode === 'manual'}
            <div class="deploy-steps">
              <div class="deploy-step">
                <div class="deploy-step-number">1</div>
                <div class="deploy-step-content">
                  <h4>Install the CLI</h4>
                  <div class="code-block">
                    <code>pip install realms-gos</code>
                    <button type="button" class="copy-btn" on:click={() => copyToClipboard('pip install realms-gos')} aria-label="Copy command">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <div class="deploy-step">
                <div class="deploy-step-number">2</div>
                <div class="deploy-step-content">
                  <h4>Create and Deploy</h4>
                  <div class="code-block">
                    <code>realms realm create --deploy --network staging</code>
                    <button type="button" class="copy-btn" on:click={() => copyToClipboard('realms realm create --deploy --network staging')} aria-label="Copy command">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" class="docs-link" on:click|stopPropagation>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              View Documentation
            </a>

            <div class="download-config-inline">
              <div class="download-config-text">
                <strong>Download Configuration</strong>
                <span>Download your realm configuration to use with the CLI or save for later.</span>
              </div>
              <button type="button" class="btn btn-small" on:click|stopPropagation={handleSubmit} disabled={isSubmitting}>
                {#if isSubmitting}
                  <span class="spinner-small"></span>
                {:else}
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Download
                {/if}
              </button>
            </div>
            {/if}
          </div>
        </div>

        {#if submitError}
          <div class="error-banner">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            {submitError}
          </div>
        {/if}
      </div>
    {/if}
  </div>

</div>

<style>
  .wizard-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
  }

  .wizard-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #525252;
    text-decoration: none;
    font-size: 0.875rem;
    margin-bottom: 1rem;
    transition: color 0.15s;
  }

  .back-link:hover {
    color: #171717;
  }

  .wizard-header h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #171717;
    margin: 0 0 0.5rem;
  }

  .subtitle {
    color: #737373;
    margin: 0;
  }

  /* Steps */
  .steps-container {
    margin-bottom: 2rem;
  }

  .steps {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
  }

  .step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem 1rem;
    transition: all 0.15s;
  }

  .step:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .step-number {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #E5E5E5;
    color: #737373;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
    transition: all 0.15s;
  }

  .step.active .step-number {
    background: #171717;
    color: #FFFFFF;
  }

  .step.completed .step-number {
    background: #22C55E;
    color: #FFFFFF;
  }

  .step-label {
    font-size: 0.75rem;
    color: #737373;
    font-weight: 500;
  }

  .step.active .step-label {
    color: #171717;
  }

  .step-connector {
    width: 60px;
    height: 2px;
    background: #E5E5E5;
    margin: 0 -0.5rem;
    margin-bottom: 1.5rem;
  }

  .step-connector.completed {
    background: #22C55E;
  }

  /* Form */
  .form-container {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 2rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
  }

  .form-step h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 0.25rem;
  }

  .step-description {
    color: #737373;
    margin: 0 0 1.5rem;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  .form-group label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: #171717;
    margin-bottom: 0.5rem;
  }

  .required {
    color: #EF4444;
  }

  .form-group input[type="text"],
  .form-group input[type="number"],
  .form-group textarea {
    width: 100%;
    padding: 0.75rem 1rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    font-size: 1rem;
    transition: all 0.15s;
    background: #FAFAFA;
  }

  .form-group input:focus,
  .form-group textarea:focus {
    outline: none;
    border-color: #171717;
    background: #FFFFFF;
  }

  .form-group input.error,
  .form-group textarea.error {
    border-color: #EF4444;
  }

  .error-message {
    color: #EF4444;
    font-size: 0.75rem;
    margin-top: 0.25rem;
    display: block;
  }

  .char-count {
    font-size: 0.75rem;
    color: #A3A3A3;
    float: right;
    margin-top: 0.25rem;
  }

  .hint {
    font-size: 0.75rem;
    color: #737373;
    margin-top: 0.25rem;
    display: block;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  @media (max-width: 600px) {
    .form-row {
      grid-template-columns: 1fr;
    }
  }

  /* Upload Area */
  .upload-area {
    position: relative;
    border: 2px dashed #E5E5E5;
    border-radius: 0.75rem;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.15s;
    min-height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .upload-area:hover {
    border-color: #A3A3A3;
  }

  .upload-area.has-preview {
    padding: 0.5rem;
    border-style: solid;
  }

  .upload-area input[type="file"] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }

  .upload-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    color: #737373;
  }

  .upload-placeholder span {
    font-size: 0.875rem;
  }

  .upload-placeholder .hint {
    font-size: 0.75rem;
    color: #A3A3A3;
  }

  .preview-image {
    max-width: 100%;
    max-height: 140px;
    border-radius: 0.5rem;
    object-fit: contain;
  }

  .welcome-upload .preview-image {
    max-height: 100px;
    width: 100%;
    object-fit: cover;
  }

  .remove-btn {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: rgba(0, 0, 0, 0.7);
    color: #FFFFFF;
    border: none;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s;
  }

  .remove-btn:hover {
    background: #EF4444;
  }

  /* Toggle */
  .toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
  }

  .toggle-label input[type="checkbox"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    pointer-events: none;
  }

  .toggle-label > span:last-child {
    flex: 1;
  }

  .toggle-switch {
    width: 44px;
    min-width: 44px;
    flex-shrink: 0;
    height: 24px;
    background: #E5E5E5;
    border-radius: 12px;
    position: relative;
    transition: background 0.2s;
    display: inline-block;
  }

  .toggle-switch::after {
    content: '';
    position: absolute;
    width: 20px;
    height: 20px;
    background: #FFFFFF;
    border-radius: 50%;
    top: 2px;
    left: 2px;
    transition: transform 0.2s;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  .toggle-label input:checked + .toggle-switch {
    background: #171717;
  }

  .toggle-label input:checked + .toggle-switch::after {
    transform: translateX(20px);
  }

  .divider {
    height: 1px;
    background: #E5E5E5;
    margin: 1.5rem 0;
  }

  /* Language Selection */
  .language-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .language-chip {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #FAFAFA;
    border: 2px solid #E5E5E5;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.875rem;
  }

  .language-chip:hover {
    border-color: #A3A3A3;
  }

  .language-chip.selected {
    background: #F0FDF4;
    border-color: #22C55E;
  }

  .lang-code {
    font-size: 0.75rem;
    font-weight: 700;
    background: #E5E5E5;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    color: #525252;
  }

  .language-chip.selected .lang-code {
    background: #D1FAE5;
    color: #059669;
  }

  .lang-code-small {
    font-size: 0.625rem;
    font-weight: 700;
    background: #E5E5E5;
    padding: 0.125rem 0.25rem;
    border-radius: 0.125rem;
    color: #525252;
  }

  .lang-name {
    color: #171717;
  }

  .lang-check {
    color: #22C55E;
    font-weight: 600;
    font-size: 0.75rem;
  }

  /* Multi-language inputs */
  .multilang-inputs {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .multilang-input {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .multilang-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #525252;
  }

  .multilang-label .lang-code-small {
    font-size: 0.625rem;
  }

  .token-section {
    margin-bottom: 0.5rem;
  }

  .token-config {
    background: #F5F5F5;
    border-radius: 0.75rem;
    padding: 1.25rem;
    margin-top: 1rem;
  }

  .land-token-config {
    background: #F5F5F5;
    border-radius: 0.75rem;
    padding: 1.25rem;
    margin-top: 1rem;
  }

  /* Review */
  .review-card {
    background: #FAFAFA;
    border-radius: 0.75rem;
    overflow: hidden;
  }

  .review-header {
    display: flex;
    gap: 1rem;
    padding: 1.5rem;
    align-items: flex-start;
  }

  .review-logo {
    width: 64px;
    height: 64px;
    border-radius: 0.75rem;
    object-fit: cover;
    flex-shrink: 0;
  }

  .review-logo-placeholder {
    width: 64px;
    height: 64px;
    background: #E5E5E5;
    border-radius: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #A3A3A3;
    flex-shrink: 0;
  }

  .review-header h3 {
    margin: 0 0 0.25rem;
    font-size: 1.25rem;
    color: #171717;
  }

  .review-description {
    margin: 0;
    color: #737373;
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .review-welcome-image {
    padding: 0 1.5rem;
  }

  .review-welcome-image img {
    width: 100%;
    height: 120px;
    object-fit: cover;
    border-radius: 0.5rem;
  }

  .review-section {
    padding: 1rem 1.5rem;
    border-top: 1px solid #E5E5E5;
  }

  .review-section h4 {
    margin: 0 0 0.5rem;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #737373;
  }

  .review-section p {
    margin: 0;
    color: #171717;
  }

  .review-tokens {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .token-badge {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    padding: 0.75rem 1rem;
    min-width: 120px;
  }

  .token-badge.land {
    background: #FEF3C7;
    border-color: #F59E0B;
  }

  .token-symbol {
    font-weight: 700;
    font-size: 1rem;
    color: #171717;
  }

  .token-name {
    font-size: 0.75rem;
    color: #737373;
  }

  .token-supply {
    font-size: 0.625rem;
    color: #A3A3A3;
  }

  .error-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: #FEF2F2;
    border: 1px solid #FECACA;
    color: #DC2626;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
    font-size: 0.875rem;
  }

  /* Navigation */
  .wizard-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .wizard-nav-top {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #E5E5E5;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 0.9375rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    border: none;
  }

  .btn-primary {
    background: #171717;
    color: #FFFFFF;
  }

  .btn-primary:hover {
    background: #404040;
  }

  .btn-primary:disabled {
    background: #A3A3A3;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: #FFFFFF;
    color: #525252;
    border: 1px solid #E5E5E5;
  }

  .btn-secondary:hover {
    border-color: #525252;
    color: #171717;
  }

  .btn-outline {
    background: #FFFFFF;
    color: #171717;
    border: 1px solid #E5E5E5;
  }

  .btn-outline:hover {
    background: #F5F5F5;
    border-color: #D4D4D4;
  }

  .btn-create {
    background: #22C55E;
  }

  .btn-create:hover {
    background: #16A34A;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #FFFFFF;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* File upload with info */
  .file-upload.has-file {
    border-style: solid;
    border-color: #22C55E;
    background: #F0FDF4;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    width: 100%;
  }

  .file-info span {
    flex: 1;
    font-size: 0.875rem;
    color: #171717;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .remove-file-btn {
    background: none;
    border: none;
    color: #737373;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: all 0.15s;
  }

  .remove-file-btn:hover {
    color: #EF4444;
    background: #FEE2E2;
  }

  /* Source tabs for codex */
  .source-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .source-tab {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    background: #FAFAFA;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    color: #525252;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .source-tab:hover {
    border-color: #A3A3A3;
  }

  .source-tab.active {
    background: #171717;
    border-color: #171717;
    color: #FFFFFF;
  }

  /* Codex selection */
  .codex-options {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .codex-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    border: 2px solid #E5E5E5;
    border-radius: 0.5rem;
    background: #FFFFFF;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
  }

  .codex-card:hover {
    border-color: #A3A3A3;
  }

  .codex-card.selected {
    background: #F0FDF4;
    border-color: #22C55E;
  }

  .codex-radio {
    width: 20px;
    height: 20px;
    min-width: 20px;
    border: 2px solid #D4D4D4;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 0.125rem;
  }

  .codex-card.selected .codex-radio {
    border-color: #22C55E;
  }

  .codex-radio-dot {
    width: 10px;
    height: 10px;
    background: #22C55E;
    border-radius: 50%;
  }

  .codex-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .codex-name {
    font-weight: 600;
    color: #171717;
    font-size: 0.9375rem;
  }

  .codex-desc {
    font-size: 0.8125rem;
    color: #737373;
  }

  .doc-link {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: #2563EB;
    text-decoration: none;
    margin-top: 0.25rem;
  }

  .doc-link:hover {
    text-decoration: underline;
  }

  /* Select all row */
  .select-all-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding: 0.75rem 1rem;
    background: #F5F5F5;
    border-radius: 0.5rem;
  }

  .selected-count {
    font-size: 0.875rem;
    color: #525252;
  }

  /* Extension categories */
  .extension-category {
    margin-bottom: 1.5rem;
  }

  .category-title {
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 0.25rem 0;
  }

  .category-desc {
    font-size: 0.8125rem;
    color: #737373;
    margin: 0 0 0.75rem 0;
  }

  /* Extensions grid */
  .extensions-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }

  @media (max-width: 600px) {
    .extensions-grid {
      grid-template-columns: 1fr;
    }
  }

  .extension-card {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    background: #FAFAFA;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
  }

  .extension-card:hover {
    border-color: #A3A3A3;
  }

  .extension-card.selected {
    background: #F0FDF4;
    border-color: #22C55E;
  }

  .extension-card.mandatory {
    cursor: default;
    opacity: 0.9;
  }

  .extension-card.mandatory:hover {
    border-color: #22C55E;
  }

  .mandatory-badge {
    display: inline-block;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    background: #22C55E;
    color: white;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    margin-left: 0.5rem;
    vertical-align: middle;
  }

  .extension-check {
    width: 20px;
    height: 20px;
    min-width: 20px;
    border: 2px solid #D4D4D4;
    border-radius: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 0.125rem;
  }

  .extension-card.selected .extension-check {
    background: #22C55E;
    border-color: #22C55E;
    color: #FFFFFF;
  }

  .extension-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .extension-name {
    font-weight: 500;
    color: #171717;
    font-size: 0.9375rem;
  }

  .extension-desc {
    font-size: 0.75rem;
    color: #737373;
    line-height: 1.4;
  }

  /* Custom extensions section */
  .custom-extensions-section {
    margin-top: 1rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .section-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
  }

  .btn-small {
    padding: 0.5rem 1rem;
    font-size: 0.8125rem;
    background: #FAFAFA;
    border: 1px solid #E5E5E5;
    color: #525252;
  }

  .btn-small:hover {
    border-color: #525252;
    color: #171717;
  }

  .empty-state {
    text-align: center;
    color: #A3A3A3;
    font-size: 0.875rem;
    padding: 2rem;
    background: #FAFAFA;
    border-radius: 0.5rem;
  }

  .custom-extension-row {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
    padding: 1rem;
    background: #FAFAFA;
    border-radius: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .custom-extension-row .form-group {
    margin-bottom: 0;
  }

  .custom-extension-row .form-group label {
    font-size: 0.75rem;
    margin-bottom: 0.25rem;
  }

  .custom-extension-row input[type="text"] {
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
  }

  .flex-grow {
    flex: 1;
  }

  .mini-tabs {
    display: flex;
  }

  .mini-tab {
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    color: #525252;
    cursor: pointer;
    transition: all 0.15s;
  }

  .mini-tab:first-child {
    border-radius: 0.25rem 0 0 0.25rem;
  }

  .mini-tab:last-child {
    border-radius: 0 0.25rem 0.25rem 0;
    border-left: none;
  }

  .mini-tab.active {
    background: #171717;
    border-color: #171717;
    color: #FFFFFF;
  }

  .file-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: #E5E5E5;
    border-radius: 0.25rem;
    font-size: 0.8125rem;
  }

  .file-pill button {
    background: none;
    border: none;
    color: #737373;
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0;
  }

  .file-pill button:hover {
    color: #EF4444;
  }

  .remove-ext-btn {
    background: none;
    border: none;
    color: #A3A3A3;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.25rem;
    transition: all 0.15s;
  }

  .remove-ext-btn:hover {
    color: #EF4444;
    background: #FEE2E2;
  }

  /* Review extensions */
  .review-extensions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .extension-pill {
    padding: 0.375rem 0.75rem;
    background: #E5E5E5;
    border-radius: 1rem;
    font-size: 0.75rem;
    color: #525252;
  }

  .extension-pill.custom {
    background: #DBEAFE;
    color: #1D4ED8;
  }

  .review-file {
    margin-top: 0.75rem;
    font-size: 0.875rem;
  }

  /* Deploy Step */
  .deploy-options {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .deploy-option {
    background: #FAFAFA;
    border: 1px solid #E5E5E5;
    border-radius: 0.75rem;
    padding: 1.25rem;
    transition: all 0.15s;
  }

  .deploy-option.coming-soon {
    opacity: 0.6;
  }

  .deploy-option.active {
    background: #FFFFFF;
    border-color: #171717;
  }

  .deploy-option-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .deploy-option-icon {
    width: 48px;
    height: 48px;
    min-width: 48px;
    background: #F5F5F5;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #525252;
  }

  .deploy-option.active .deploy-option-icon {
    background: #171717;
    color: #FFFFFF;
  }

  .deploy-option-header h3 {
    margin: 0 0 0.25rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: #171717;
  }

  .badge-coming-soon {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    background: #FEF3C7;
    color: #92400E;
    font-size: 0.6875rem;
    font-weight: 500;
    border-radius: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .badge-recommended {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    background: #DCFCE7;
    color: #166534;
    font-size: 0.6875rem;
    font-weight: 500;
    border-radius: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .badge-warning {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    background: #FEF3C7;
    color: #92400E;
    font-size: 0.6875rem;
    font-weight: 500;
    border-radius: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .badge-developer {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    background: #E0E7FF;
    color: #3730A3;
    font-size: 0.6875rem;
    font-weight: 500;
    border-radius: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .deploy-option.disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .deploy-requirement {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    background: #FEF3C7;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    color: #92400E;
  }

  .deploy-requirement span {
    flex: 1;
  }

  .btn-dark {
    background: #171717;
    color: #FFFFFF;
    border: none;
  }

  .btn-dark:hover {
    background: #404040;
  }

  button.deploy-option {
    width: 100%;
    text-align: left;
    cursor: pointer;
  }

  .deploy-option-desc {
    margin: 0;
    color: #737373;
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .deploy-steps {
    margin-top: 1.5rem;
  }

  .deploy-step {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }

  .deploy-step:last-child {
    margin-bottom: 0;
  }

  .deploy-step-number {
    width: 28px;
    height: 28px;
    min-width: 28px;
    background: #171717;
    color: #FFFFFF;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8125rem;
    font-weight: 600;
  }

  .deploy-step-content {
    flex: 1;
  }

  .deploy-step-content h4 {
    margin: 0 0 0.5rem;
    font-size: 0.9375rem;
    font-weight: 500;
    color: #171717;
  }

  .code-block {
    display: flex;
    align-items: center;
    background: #171717;
    border-radius: 0.5rem;
    padding: 0.75rem 1rem;
    gap: 0.75rem;
  }

  .code-block code {
    flex: 1;
    color: #FFFFFF;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.875rem;
    white-space: nowrap;
    overflow-x: auto;
  }

  .copy-btn {
    background: none;
    border: none;
    color: #737373;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: all 0.15s;
    flex-shrink: 0;
  }

  .copy-btn:hover {
    color: #FFFFFF;
    background: rgba(255, 255, 255, 0.1);
  }

  .docs-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1.25rem;
    color: #525252;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    transition: color 0.15s;
  }

  .docs-link:hover {
    color: #171717;
  }

  .download-config-inline {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1.25rem;
    padding: 1rem;
    background: #F5F5F5;
    border-radius: 0.5rem;
  }

  .download-config-text {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .download-config-text strong {
    font-size: 0.875rem;
    color: #171717;
  }

  .download-config-text span {
    font-size: 0.75rem;
    color: #737373;
  }

  .spinner-small {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-top-color: #525252;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  /* Assistant Cards */
  .assistant-options {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .assistant-card {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1.25rem;
    background: #FAFAFA;
    border: 2px solid #E5E5E5;
    border-radius: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
    width: 100%;
  }

  .assistant-card:hover {
    border-color: #A3A3A3;
  }

  .assistant-card.selected {
    background: #F0FDF4;
    border-color: #22C55E;
  }

  .assistant-check {
    width: 24px;
    height: 24px;
    min-width: 24px;
    border: 2px solid #D4D4D4;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 0.25rem;
  }

  .assistant-card.selected .assistant-check {
    background: #22C55E;
    border-color: #22C55E;
    color: #FFFFFF;
  }

  .assistant-info {
    display: flex;
    gap: 1rem;
    flex: 1;
  }

  .assistant-avatar {
    font-size: 2.5rem;
    line-height: 1;
  }

  .assistant-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
  }

  .assistant-name {
    font-weight: 600;
    font-size: 1.125rem;
    color: #171717;
  }

  .assistant-desc {
    font-size: 0.875rem;
    color: #737373;
    line-height: 1.5;
  }

  .assistant-features {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .feature-tag {
    padding: 0.25rem 0.625rem;
    background: #E5E5E5;
    border-radius: 1rem;
    font-size: 0.75rem;
    color: #525252;
  }

  .assistant-card.selected .feature-tag {
    background: #DCFCE7;
    color: #166534;
  }

  /* Inline Assistant Selection (inside Extensions) */
  .section-title {
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 0.25rem;
  }

  .section-desc {
    font-size: 0.875rem;
    color: #737373;
    margin: 0 0 1rem;
  }

  .assistant-inline-options {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .assistant-inline-card {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1rem;
    background: #FAFAFA;
    border: 2px solid #E5E5E5;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .assistant-inline-card:hover {
    border-color: #A3A3A3;
  }

  .assistant-inline-card.selected {
    background: #F0FDF4;
    border-color: #22C55E;
  }

  .assistant-inline-check {
    width: 18px;
    height: 18px;
    min-width: 18px;
    border: 2px solid #D4D4D4;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.625rem;
    color: transparent;
  }

  .assistant-inline-card.selected .assistant-inline-check {
    background: #22C55E;
    border-color: #22C55E;
    color: #FFFFFF;
  }

  .assistant-inline-icon {
    font-size: 1.25rem;
  }

  .assistant-inline-name {
    font-weight: 500;
    color: #171717;
  }

  .assistant-selected-info {
    margin-top: 1rem;
    padding: 0.875rem;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    border-radius: 0.5rem;
  }

  .assistant-selected-info p {
    margin: 0 0 0.75rem;
    font-size: 0.8125rem;
    color: #166534;
    line-height: 1.5;
  }

  .assistant-features-inline {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .feature-tag-inline {
    padding: 0.25rem 0.625rem;
    background: #DCFCE7;
    border-radius: 1rem;
    font-size: 0.6875rem;
    color: #166534;
  }

  /* Data Upload Section */
  .data-upload-section {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .data-info-box {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-radius: 0.5rem;
  }

  .data-info-icon {
    width: 48px;
    height: 48px;
    min-width: 48px;
    background: #0EA5E9;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
  }

  .data-info-text {
    flex: 1;
  }

  .data-info-text strong {
    display: block;
    font-size: 0.9375rem;
    color: #0C4A6E;
    margin-bottom: 0.25rem;
  }

  .data-info-text p {
    margin: 0;
    font-size: 0.8125rem;
    color: #0369A1;
    line-height: 1.5;
  }

  .file-uploaded {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    border-radius: 0.5rem;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: #166534;
  }

  .file-info span {
    font-weight: 500;
  }

  .remove-file-btn {
    background: none;
    border: none;
    color: #DC2626;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 0.25rem;
    transition: background 0.15s;
  }

  .remove-file-btn:hover {
    background: #FEE2E2;
  }

  .optional-note {
    margin: 0;
    font-size: 0.8125rem;
    color: #737373;
    text-align: center;
    font-style: italic;
  }

  .download-manifest-section {
    text-align: center;
    padding: 1rem 0;
  }

  .download-manifest-section h3 {
    margin: 0 0 0.25rem;
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
  }

  .download-manifest-section p {
    margin: 0 0 1rem;
    color: #737373;
    font-size: 0.875rem;
  }

  /* Automatic Deployment Styles */
  .deploy-action {
    margin-top: 1rem;
    padding: 1rem;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    border-radius: 0.5rem;
    text-align: center;
  }

  .deploy-cost {
    margin: 0 0 1rem;
    color: #166534;
    font-size: 0.875rem;
  }

  .btn-deploy {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
  }

  .deploy-error {
    margin: 1rem 0 0;
    color: #DC2626;
    font-size: 0.875rem;
  }

  .deploy-success {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1rem;
    padding: 1rem;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    border-radius: 0.5rem;
    color: #166534;
  }

  .deploy-success svg {
    color: #22C55E;
    flex-shrink: 0;
  }

  .deploy-success a {
    color: #166534;
    font-weight: 500;
    text-decoration: underline;
  }

  .deploy-success.deploy-in-progress {
    background: #FEF3C7;
    border-color: #FCD34D;
    color: #92400E;
    flex-direction: column;
    align-items: flex-start;
  }

  .deploy-success.deploy-in-progress svg {
    color: #F59E0B;
  }

  .deploy-success.deploy-in-progress svg.spinning {
    animation: spin 1s linear infinite;
  }

  .deploy-success .deploy-info {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    opacity: 0.9;
  }

  .deploy-success .btn {
    margin-top: 0.5rem;
  }

  .spinner-small {
    width: 16px;
    height: 16px;
    border: 2px solid #FFFFFF;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 600px) {
    .wizard-container {
      padding: 1rem;
    }

    .form-container {
      padding: 1.25rem;
    }

    .steps {
      gap: 0;
    }

    .step {
      padding: 0.25rem 0.5rem;
    }

    .step-label {
      display: none;
    }

    .step-connector {
      width: 30px;
      margin-bottom: 0;
    }

    .source-tabs {
      flex-direction: column;
    }

    .custom-extension-row {
      flex-direction: column;
      align-items: stretch;
    }

    .remove-ext-btn {
      align-self: flex-end;
    }
  }
</style>
