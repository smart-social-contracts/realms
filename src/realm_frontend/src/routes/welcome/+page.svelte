<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { _ } from 'svelte-i18n';
  import T from '$lib/components/T.svelte';
  import { Button } from 'flowbite-svelte';
  
  let isMobile = false;
  let videoElement;
  
  // Check for mobile viewport on client-side only
  onMount(() => {
    if (browser) {
      const checkMobile = () => {
        isMobile = window.innerWidth < 768;
      };
      
      // Initial check
      checkMobile();
      
      // Add resize listener
      window.addEventListener('resize', checkMobile);
      
      // Apply slow motion effect
      if (videoElement) {
        videoElement.playbackRate = 0.3; // Slow motion effect (30% of normal speed)
      }
      
      // Cleanup
      return () => {
        window.removeEventListener('resize', checkMobile);
      };
    }
  });
</script>

<svelte:head>
  <title>{$_('common.welcome')}</title>
</svelte:head>

<div class="welcome-container">
  {#if browser}
    <video 
      bind:this={videoElement}
      autoplay 
      muted 
      loop 
      playsinline
      class="background-video"
      src={isMobile ? '/videos/video_vertical.mp4' : '/videos/video_horizontal.mp4'}
    >
      <track kind="captions">
    </video>
    <div class="video-overlay"></div>
  {/if}
  
  <div class="content">
    <h1>
      <T key="common.welcome" />
    </h1>
    
    <div class="button-container">
      <a href="/app-sidebar/citizen" class="btn btn-member">
        <T key="navigation.dashboard" default_text="Access as a Member" />
      </a>
      <a href="/app/visitor" class="btn btn-visitor">
        <T key="navigation.explore" default_text="Access as a Visitor" />
      </a>
    </div>
  </div>
</div>

<div class="container mx-auto my-8 px-4">
  <h1 class="mb-6 text-3xl font-bold">
    <T key="common.welcome" />
  </h1>
  
  <div class="grid gap-6 md:grid-cols-2">
    <div class="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
      <h2 class="mb-4 text-xl font-semibold">{$_('navigation.dashboard')}</h2>
      <p class="mb-4">
        {$_('common.loading')}
      </p>
      <Button color="primary">
        {$_('buttons.submit')}
      </Button>
    </div>
    
    <div class="rounded-lg bg-white p-6 shadow-md dark:bg-gray-800">
      <h2 class="mb-4 text-xl font-semibold">{$_('navigation.explore')}</h2>
      <p class="mb-4">
        {$_('common.search')}
      </p>
      <Button color="alternative">
        {$_('buttons.cancel')}
      </Button>
    </div>
  </div>
  
  <div class="mt-8 rounded-lg bg-gray-100 p-4 dark:bg-gray-700">
    <p class="text-center text-sm text-gray-600 dark:text-gray-400">
      {$_('common.home')} | {$_('common.profile')} | {$_('common.settings')}
    </p>
  </div>
</div>

<style>
  .welcome-container {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .background-video {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: -2;
  }
  
  .video-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7); /* Dark overlay */
    z-index: -1;
  }

  .content {
    position: relative;
    z-index: 1;
    text-align: center;
    color: #ffffff;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  h1 {
    font-size: 3rem;
    margin-bottom: 2rem;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  }
  
  .button-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 1rem;
    width: 100%;
    max-width: 300px;
  }
  
  .btn {
    display: inline-block;
    padding: 1rem 1.5rem;
    text-decoration: none;
    border-radius: 30px;
    font-weight: 600;
    transition: all 0.3s ease;
    text-align: center;
    letter-spacing: 0.5px;
  }
  
  .btn-member {
    background-color: rgba(59, 130, 246, 0.8);
    color: white;
    border: 2px solid rgba(59, 130, 246, 0.9);
  }
  
  .btn-member:hover {
    background-color: rgba(59, 130, 246, 1);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  }
  
  .btn-visitor {
    background-color: transparent;
    color: white;
    border: 2px solid rgba(255, 255, 255, 0.6);
  }
  
  .btn-visitor:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.8);
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  }
  
  /* For mobile screens */
  @media (max-width: 767px) {
    h1 {
      font-size: 2rem;
      margin-bottom: 1.5rem;
    }
    
    .button-container {
      max-width: 250px;
    }
    
    .btn {
      padding: 0.8rem 1.2rem;
    }
  }
</style>
