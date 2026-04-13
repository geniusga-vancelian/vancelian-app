/**
 * Compile MJML to HTML using npx mjml
 * Runs in Node.js environment (server-side only)
 */
import { spawn } from 'child_process'
import { writeFile, unlink } from 'fs/promises'
import { tmpdir } from 'os'
import { join } from 'path'

export async function compileMjml(mjml: string): Promise<{ html: string; error: string | null }> {
  return new Promise((resolve) => {
    // Use spawn to pass MJML via stdin
    const child = spawn('npx', ['--yes', 'mjml', '-i', '-'], {
      cwd: process.cwd(),
      env: { ...process.env, NODE_ENV: process.env.NODE_ENV || 'development' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    
    let stdout = ''
    let stderr = ''
    let timeoutId: NodeJS.Timeout | null = null
    
    // Set timeout
    timeoutId = setTimeout(() => {
      child.kill()
      resolve({
        html: generateFallbackHtml('MJML compilation timeout (15s)'),
        error: 'Timeout',
      })
    }, 15000)
    
    // Collect stdout
    child.stdout.on('data', (data) => {
      stdout += data.toString()
    })
    
    // Collect stderr
    child.stderr.on('data', (data) => {
      stderr += data.toString()
    })
    
    // Handle completion
    child.on('close', (code) => {
      if (timeoutId) clearTimeout(timeoutId)
      
      if (code !== 0) {
        const errorMsg = stderr || `Process exited with code ${code}`
        console.error('[MJML] Compilation error:', errorMsg)
        resolve({
          html: generateFallbackHtml(errorMsg),
          error: errorMsg,
        })
        return
      }
      
      // Check if we got valid HTML output
      const output = stdout.trim()
      if (output.length > 0 && (output.includes('<!DOCTYPE') || output.includes('<html'))) {
        resolve({
          html: output,
          error: null,
        })
        return
      }
      
      // If stderr but no stdout, or invalid output
      if (stderr) {
        console.warn('[MJML] Compilation warning:', stderr)
      }
      
      resolve({
        html: generateFallbackHtml(stderr || 'No valid HTML output from MJML'),
        error: stderr || 'No valid HTML output',
      })
    })
    
    // Handle spawn errors
    child.on('error', (error) => {
      if (timeoutId) clearTimeout(timeoutId)
      const errorMsg = error.message || String(error)
      console.error('[MJML] Spawn error:', errorMsg)
      resolve({
        html: generateFallbackHtml(errorMsg),
        error: errorMsg,
      })
    })
    
    // Write MJML to stdin
    child.stdin.write(mjml, 'utf-8')
    child.stdin.end()
  })
}

function generateFallbackHtml(errorMsg: string): string {
  return `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Preview</title>
</head>
<body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 4px;">
        <h2 style="color: #d32f2f; margin-bottom: 20px;">MJML Compilation Error</h2>
        <p style="color: #666; line-height: 1.6;">${escapeHtml(errorMsg)}</p>
        <p style="color: #999; font-size: 14px; margin-top: 20px;">Please ensure Node.js and MJML are installed, or check the server logs for details.</p>
    </div>
</body>
</html>`
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

