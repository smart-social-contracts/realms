<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  
  let isMobile = false;
  
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
      
      // Cleanup
      return () => {
        window.removeEventListener('resize', checkMobile);
      };
    }
  });
</script>

<svelte:head>
  <title>Welcome</title>
</svelte:head>

<div class="welcome-container">
  {#if browser}
    <video 
      autoplay 
      muted 
      loop 
      playsinline
      class="background-video"
      src={isMobile ? '/videos/video_vertical.mp4' : '/videos/video_horizontal.mp4'}
    >
      <track kind="captions">
    </video>
  {/if}
  
  <div class="content">
    <h1>Welcome</h1>
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
    z-index: -1;
  }

  .content {
    position: relative;
    z-index: 1;
    text-align: center;
    color: #ffffff;
    padding: 2rem;
  }

  h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  }
  
  /* For mobile screens */
  @media (max-width: 767px) {
    h1 {
      font-size: 2rem;
    }
  }
</style>
