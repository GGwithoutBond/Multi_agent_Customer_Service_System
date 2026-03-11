<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { login } from '@/api/auth'
import { useMessage, NIcon } from 'naive-ui'
import { EyeOutline, EyeOffOutline } from '@vicons/ionicons5'

const router = useRouter()
const userStore = useUserStore()
const message = useMessage()

// States
const loading = ref(false)
const showPassword = ref(false)
const loginFailed = ref(false)
const activeInput = ref<string | null>(null)

// Refs
const emailInput = ref<HTMLElement | null>(null)
const passwordInput = ref<HTMLElement | null>(null)

const form = reactive({
  email: '',
  password: ''
})

// Mouse and eye tracking
const mouseX = ref(window.innerWidth / 2)
const mouseY = ref(window.innerHeight / 2)
const groupCenter = ref({ x: window.innerWidth * 0.25, y: window.innerHeight * 0.5 })

// Computed overall animation state
const characterStateClass = computed(() => {
  if (loginFailed.value) return 'state-failed';
  if (activeInput.value === 'password' && showPassword.value) return 'state-show-password';
  if (activeInput.value === 'password') return 'state-focus-password';
  if (activeInput.value === 'email') return 'state-focus-email';
  return 'state-idle';
})

// Watchers to drop loginFailed state when user starts typing again
watch(() => form.email, () => { loginFailed.value = false })
watch(() => form.password, () => { loginFailed.value = false })

const handleMouseMove = (e: MouseEvent) => {
  mouseX.value = e.clientX
  mouseY.value = e.clientY
}

const createEyeStyle = (charType: 'purple' | 'black' | 'orange' | 'yellow') => {
  return computed(() => {
    let tx = mouseX.value;
    let ty = mouseY.value;
    
    // Failed state
    if (loginFailed.value && !activeInput.value) {
      return { transform: `translate(0px, 6px)`, transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)' };
    }
    
    // Show password state
    if (characterStateClass.value === 'state-show-password') {
      if (charType === 'black') {
        return { transform: `translate(-7px, 0px)`, transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)' };
      }
      if (charType === 'purple') {
        // purple looks right (peeks)
        return { transform: `translate(7px, 0px)`, transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)' };
      }
      // orange and yellow follow mouse
    } 
    // Focus states
    else if (activeInput.value) {
      if (charType === 'purple' || charType === 'black') {
        const inputRef = activeInput.value === 'email' ? emailInput.value : passwordInput.value;
        if (inputRef) {
          const rect = inputRef.getBoundingClientRect();
          tx = rect.left + 50;
          ty = rect.top + rect.height / 2;
        }
      }
      // orange and yellow continue to follow mouse
    }
    
    const dx = tx - groupCenter.value.x;
    const dy = ty - groupCenter.value.y;
    const angle = Math.atan2(dy, dx);
    const maxRadius = (charType === 'orange' || charType === 'yellow') ? 5 : 7;
    const dist = Math.min(Math.sqrt(dx*dx + dy*dy) / 250, 1);
    const r = maxRadius * dist;
    
    const moveX = r * Math.cos(angle);
    const moveY = r * Math.sin(angle);
    
    return {
      transform: `translate(${moveX}px, ${moveY}px)`,
      transition: 'transform 0.15s ease-out'
    };
  });
};

const purplePupilStyle = createEyeStyle('purple');
const blackPupilStyle = createEyeStyle('black');
const orangePupilStyle = createEyeStyle('orange');
const yellowPupilStyle = createEyeStyle('yellow');

const updateGroupCenter = () => {
  groupCenter.value = {
    x: window.innerWidth * 0.25,
    y: window.innerHeight * 0.5
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('resize', updateGroupCenter)
  updateGroupCenter()
  mouseX.value = window.innerWidth / 2
  mouseY.value = window.innerHeight / 2
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('resize', updateGroupCenter)
})

const handleLogin = async () => {
  loading.value = true
  loginFailed.value = false // Reset before try
  
  try {
    const res: any = await login({ username: form.email, password: form.password })
    const token = res.data?.access_token || res.access_token || res.token
    if (token) {
      userStore.setToken(token)
      message.success('Login successful')
      router.push('/')
    } else {
      loginFailed.value = true // Trigger fail state
      message.error('Login failed: Invalid credentials')
    }
  } catch (error) {
    console.error(error)
    loginFailed.value = true // Trigger fail state
    message.error('Login failed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-layout">
    <div class="left-panel">
      <!-- The main state wrapper -->
      <div class="character-group" :class="characterStateClass">
        
        <!-- 1. Deep Purple Rectangle (Backest, Tilted) -->
        <div class="char purple-rect">
          <div class="eyes-container">
            <div class="eye"><div class="pupil" :style="purplePupilStyle"></div></div>
            <div class="eye"><div class="pupil" :style="purplePupilStyle"></div></div>
          </div>
          <div class="mouth purple-mouth"></div>
        </div>
        
        <!-- 2. Black Rectangle (Center) -->
        <div class="char black-rect">
          <div class="eyes-container">
             <div class="eye"><div class="pupil" :style="blackPupilStyle"></div></div>
             <div class="eye"><div class="pupil" :style="blackPupilStyle"></div></div>
          </div>
        </div>
        
        <!-- 3. Bright Orange Shape (Bottom Left, Semi-Oval) -->
        <div class="char orange-shape">
          <div class="eyes-container">
            <div class="eye"><div class="pupil" :style="orangePupilStyle"></div></div>
            <div class="eye"><div class="pupil" :style="orangePupilStyle"></div></div>
            <div class="eye"><div class="pupil" :style="orangePupilStyle"></div></div>
          </div>
        </div>
        
        <!-- 4. Sunny Yellow Blob (Right, with Beak) -->
        <div class="char yellow-blob">
          <div class="eyes-container side-eye-container">
            <div class="eye small-eye" :style="yellowPupilStyle"></div>
          </div>
          <div class="mouth beak"></div>
        </div>

      </div>
    </div>
    
    <div class="right-panel">
      <!-- Auth form content -->
      <div class="form-wrapper">
        <h1 class="welcome-title">Welcome back!</h1>
        <p class="signup-prompt">Please enter your details</p>
        
        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="input-wrapper">
            <label class="input-label">Email</label>
            <div class="input-container" :class="{ focused: activeInput === 'email', error: loginFailed }">
              <input 
                type="text" 
                v-model="form.email" 
                placeholder="anna@gmail.com" 
                required
                @focus="activeInput = 'email'"
                @blur="activeInput = null"
                ref="emailInput"
              />
            </div>
          </div>
          
          <div class="input-wrapper">
            <label class="input-label">Password</label>
            <div class="input-container" :class="{ focused: activeInput === 'password', error: loginFailed }">
              <input 
                :type="showPassword ? 'text' : 'password'" 
                v-model="form.password" 
                placeholder="••••••••" 
                required
                @focus="activeInput = 'password'"
                @blur="activeInput = null"
                ref="passwordInput"
              />
              <button type="button" class="eye-toggle" @click="showPassword = !showPassword">
                <n-icon :component="showPassword ? EyeOutline : EyeOffOutline" size="20" />
              </button>
            </div>
          </div>

          <div class="form-actions">
            <label class="remember-me">
              <input type="checkbox" checked /> Remember for 30 days
            </label>
            <a href="#" class="forgot-password">Forgot password?</a>
          </div>
          
          <button type="submit" class="submit-btn" :disabled="loading">
            {{ loading ? 'Logging In...' : 'Log In' }}
          </button>

          <button type="button" class="social-login-btn">
            <span class="g-icon">G</span> Log in with Google
          </button>

          <p class="signup-link-bottom">Don't have an account? <a href="#">Sign Up</a></p>
          
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-layout {
  display: flex;
  min-height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background-color: #f3f4f6;
}

.left-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background-color: #ededf2;
}

.character-group {
  position: relative;
  width: 440px;
  height: 480px;
  transform-origin: bottom center;
}

/* Base styles for smooth transitions */
.char, .mouth, .eye {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.char {
  position: absolute;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08), inset -4px -4px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  transform-origin: bottom center;
}

.eyes-container {
  display: flex;
  gap: 12px;
  margin-top: 15%;
}

.eye {
  width: 20px;
  height: 20px;
  background-color: #ffffff;
  border-radius: 50%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.pupil {
  width: 8px;
  height: 8px;
  background-color: #111;
  border-radius: 50%;
}

/* 1. Deep Purple Rectangle */
.purple-rect {
  width: 180px;
  height: 380px;
  background-color: #6032f6;
  top: 0;
  left: 60px;
  z-index: 10;
  transform: rotate(5deg);
}

.purple-mouth {
  width: 12px;
  height: 4px;
  background-color: #111;
  border-radius: 2px;
  margin-top: 10px;
  transition: all 0.4s ease;
}

/* 2. Black Rectangle */
.black-rect {
  width: 110px;
  height: 250px;
  background-color: #1a1b22;
  bottom: 50px;
  left: 200px;
  z-index: 20;
}
.black-rect .eyes-container {
  margin-top: 25%;
}

/* 3. Bright Orange Shape */
.orange-shape {
  width: 320px;
  height: 180px;
  background-color: #fc7528;
  border-top-left-radius: 160px;
  border-top-right-radius: 160px;
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  bottom: 50px;
  left: -20px;
  z-index: 30;
  align-items: center;
  transform-origin: bottom center;
}
.orange-shape .eyes-container {
  margin-top: 60px;
  gap: 12px;
  margin-left: 0;
  display: flex;
  justify-content: center;
  width: 100%;
}
.orange-shape .eye {
  width: 7px;
  height: 7px;
  background-color: #1a1b22;
  overflow: visible;
  position: relative;
}
.orange-shape .pupil { display: none; }
/* The third dot acts as the mouth/third eye element for the reference expression */
.orange-shape .eye:nth-child(3) {
  margin-top: 6px;
}

/* 4. Sunny Yellow Object with Beak */
.yellow-blob {
  width: 160px;
  height: 240px;
  background-color: #ecc914;
  border-top-left-radius: 120px;
  border-top-right-radius: 80px;
  bottom: 50px;
  right: -50px;
  z-index: 40;
  align-items: flex-end;
  padding-right: 40px;
  transform-origin: bottom right; /* Pinned to right corner */
}

.yellow-blob .eyes-container {
  margin-top: 40px;
}
.yellow-blob .eye {
  width: 8px;
  height: 8px;
  background-color: #1a1b22;
}
.yellow-blob .pupil { display: none; }

.beak {
  width: 36px;
  height: 6px;
  background-color: #1a1b22;
  border-radius: 4px;
  position: absolute;
  top: 60px;
  right: -5px;
}

/* --- STATE ANIMATIONS --- */

/* State: Focus Gossiping */
/* Body leans forward like a human stretching from the waist (base pinned, top moves right) */
.state-focus-email .purple-rect, .state-focus-password .purple-rect {
  transform: rotate(12deg) skewX(-5deg);
}
.state-focus-email .purple-mouth, .state-focus-password .purple-mouth {
  width: 5px;
  height: 16px;
  border-radius: 3px;
  background-color: #111;
  border-top: none;
}

.state-focus-email .black-rect, .state-focus-password .black-rect {
  transform: rotate(15deg) skewX(-5deg);
}

.state-focus-email .yellow-blob, .state-focus-password .yellow-blob {
  transform: rotate(10deg) skewX(-5deg);
}

.state-focus-email .orange-shape, .state-focus-password .orange-shape {
  transform: rotate(8deg) skewX(-5deg);
}

/* State: Show Password (Peeking and Squinting) */
.state-show-password .orange-shape .eye {
  height: 4px;
  border-radius: 2px;
  margin-top: 4px;
}
.state-show-password .orange-mouth {
  width: 14px;
  height: 6px;
  border-radius: 50%;
  border-top: 3px solid #1a1b22;
  background-color: transparent;
  transform: translateY(5px);
  box-shadow: none;
}

.state-show-password .yellow-blob .eye {
  height: 4px;
  border-radius: 2px;
  margin-top: 2px;
}

/* State: Failed (Disappointed) */
/* Squash the characters down slightly without moving the bottom base */
.state-failed .purple-rect {
  transform: rotate(2deg) scaleY(0.95);
}
.state-failed .black-rect {
  transform: scaleY(0.95);
}
.state-failed .orange-shape {
  transform: scaleY(0.90);
}
.state-failed .yellow-blob {
  transform: scaleY(0.95);
}

/* Sad purple */
.state-failed .purple-mouth {
  width: 14px;
  height: 6px;
  border-radius: 50%;
  border-top: 3px solid #111;
  background-color: transparent;
  transform: translateY(10px);
}

/* Sad orange */
.state-failed .orange-mouth {
  width: 14px;
  height: 6px;
  border-radius: 50%;
  border-top: 3px solid #1a1b22;
  background-color: transparent;
  transform: translateY(5px);
  box-shadow: none;
}

/* Sad yellow */
.state-failed .beak {
  transform: rotate(20deg) translateY(5px);
}

/* Sad eyes overrides */
.state-failed .eye {
  border-radius: 100px 100px 10px 10px;
}


/* --- Right Panel Minimalist Form --- */
.right-panel {
  flex: 1;
  background-color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top-left-radius: 30px;
  border-bottom-left-radius: 30px;
  box-shadow: -10px 0 40px rgba(0,0,0,0.05);
}

.form-wrapper {
  width: 100%;
  max-width: 360px;
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  color: #1a1b22;
  margin: 0 0 8px 0;
  text-align: center;
}

.signup-prompt {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 40px 0;
  text-align: center;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-size: 12px;
  font-weight: 600;
  color: #1a1b22;
}

.input-container {
  position: relative;
  border-bottom: 2px solid #e5e7eb;
  transition: all 0.3s ease;
}

.input-container.focused {
  border-bottom-color: #1a1b22;
}

.input-container.error {
  border-bottom-color: #ef4444;
}

.input-container input {
  width: 100%;
  padding: 8px 0 12px;
  border: none;
  outline: none;
  font-size: 15px;
  color: #1a1b22;
  font-weight: 500;
  background: transparent;
}

.input-container input::placeholder {
  color: #9ca3af;
  font-weight: 400;
  font-family: monospace;
}

.eye-toggle {
  position: absolute;
  right: 0;
  bottom: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: #1a1b22;
  padding: 4px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  margin-top: -10px;
}

.remember-me {
  color: #4b5563;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.forgot-password {
  color: #9ca3af;
  text-decoration: none;
}

.submit-btn {
  margin-top: 10px;
  background-color: #1a1b22;
  color: #ffffff;
  border: none;
  border-radius: 20px;
  padding: 16px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.submit-btn:hover { background-color: #333; }
.submit-btn:active { transform: scale(0.98); }

.social-login-btn {
  background-color: #f3f4f6;
  color: #1a1b22;
  border: none;
  border-radius: 20px;
  padding: 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}

.social-login-btn:hover { background-color: #e5e7eb; }

.g-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: conic-gradient(from -45deg, #ea4335 110deg, #4285f4 90deg 180deg, #34a853 180deg 270deg, #fbbc05 270deg) 73% 55%/150% 150% no-repeat;
  color: white;
  font-size: 10px;
  font-weight: bold;
}

.signup-link-bottom {
  text-align: center;
  font-size: 12px;
  color: #6b7280;
  margin-top: 20px;
}
.signup-link-bottom a {
  color: #1a1b22;
  font-weight: 600;
  text-decoration: none;
}
</style>
