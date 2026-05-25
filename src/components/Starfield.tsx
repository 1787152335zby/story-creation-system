export default function Starfield() {
  return (
    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 1 }}>
      {/* Stars - using CSS box-shadow for performance */}
      <div style={{
        position: 'absolute',
        width: 1,
        height: 1,
        borderRadius: '50%',
        background: 'transparent',
        boxShadow: [
          '80px 60px 0 1.5px rgba(255,255,255,0.7)',
          '200px 120px 0 1px rgba(255,255,255,0.5)',
          '350px 80px 0 1px rgba(255,255,255,0.4)',
          '500px 150px 0 1.5px rgba(255,255,255,0.6)',
          '650px 90px 0 1px rgba(255,255,255,0.45)',
          '120px 220px 0 1px rgba(255,255,255,0.5)',
          '280px 280px 0 1px rgba(255,255,255,0.4)',
          '450px 240px 0 1.5px rgba(255,255,255,0.55)',
          '600px 320px 0 1px rgba(255,255,255,0.4)',
          '780px 180px 0 1px rgba(255,255,255,0.45)',
          '150px 380px 0 1px rgba(255,255,255,0.4)',
          '320px 420px 0 1.5px rgba(255,255,255,0.5)',
          '520px 400px 0 1px rgba(255,255,255,0.4)',
          '700px 460px 0 1px rgba(255,255,255,0.45)',
          '100px 500px 0 1px rgba(255,255,255,0.4)',
          '400px 550px 0 1px rgba(255,255,255,0.5)',
          '580px 520px 0 1.5px rgba(255,255,255,0.45)',
          '750px 580px 0 1px rgba(255,255,255,0.4)',
          '180px 620px 0 1px rgba(255,255,255,0.45)',
          '350px 680px 0 1px rgba(255,255,255,0.4)',
          '550px 640px 0 1px rgba(255,255,255,0.5)',
          '680px 700px 0 1.5px rgba(255,255,255,0.4)',
        ].join(','),
      }} />
    </div>
  )
}
