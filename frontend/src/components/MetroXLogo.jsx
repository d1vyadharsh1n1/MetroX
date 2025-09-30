import React from 'react'

export default function MetroXLogo({ size = 200, showText = true }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {/* Logo Circle */}
      <div style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
        border: '8px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
      }}>
        {/* Train Icon */}
        <div style={{
          position: 'absolute',
          width: size * 0.6,
          height: size * 0.3,
          background: 'rgba(255,255,255,0.9)',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: 'rotate(-5deg)'
        }}>
          <div style={{
            width: '80%',
            height: '60%',
            background: '#1e3a8a',
            borderRadius: '4px',
            position: 'relative'
          }}>
            {/* Train Windows */}
            <div style={{
              position: 'absolute',
              top: '20%',
              left: '15%',
              width: '25%',
              height: '40%',
              background: '#3b82f6',
              borderRadius: '2px'
            }} />
            <div style={{
              position: 'absolute',
              top: '20%',
              left: '45%',
              width: '25%',
              height: '40%',
              background: '#3b82f6',
              borderRadius: '2px'
            }} />
            <div style={{
              position: 'absolute',
              top: '20%',
              left: '75%',
              width: '25%',
              height: '40%',
              background: '#3b82f6',
              borderRadius: '2px'
            }} />
          </div>
        </div>
        
        {/* M and X Letters */}
        <div style={{
          position: 'absolute',
          fontSize: size * 0.25,
          fontWeight: 'bold',
          color: 'white',
          textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
          transform: 'translateY(-10px)'
        }}>
          MX
        </div>
      </div>
      
      {/* Text */}
      {showText && (
        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <div style={{
            fontSize: 32,
            fontWeight: 'bold',
            color: '#1e3a8a',
            letterSpacing: '2px'
          }}>
            METROX
          </div>
          <div style={{
            fontSize: 14,
            color: '#3b82f6',
            fontWeight: '500',
            letterSpacing: '1px',
            marginTop: 4
          }}>
            KOCHI METRO RAIL
          </div>
          <div style={{
            fontSize: 14,
            color: '#3b82f6',
            fontWeight: '500',
            letterSpacing: '1px'
          }}>
            TRAIN SCHEDULING
          </div>
        </div>
      )}
    </div>
  )
}
