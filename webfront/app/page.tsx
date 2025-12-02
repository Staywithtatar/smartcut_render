import Link from 'next/link'
import { Upload, Sparkles, Zap, Video } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          {/* Logo/Title */}
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl mb-8 shadow-2xl">
            <Video className="w-10 h-10 text-white" />
          </div>

          <h1 className="text-6xl font-bold text-gray-900 mb-6 leading-tight">
            AutoCut <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Influencer</span>
          </h1>

          <p className="text-2xl text-gray-600 mb-12 leading-relaxed">
            AI ตัดต่อวิดีโอให้คุณอัตโนมัติ<br />
            <span className="text-lg">เหมาะสำหรับ TikTok, Reels, Shorts</span>
          </p>

          {/* CTA Buttons */}
          <div className="flex gap-4 justify-center mb-16">
            <Link
              href="/upload"
              className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-xl hover:shadow-2xl flex items-center gap-2"
            >
              <Upload className="w-6 h-6" />
              เริ่มตัดต่อวิดีโอ
            </Link>

            <Link
              href="/dashboard"
              className="bg-white text-gray-900 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-gray-50 transition-all shadow-lg hover:shadow-xl border border-gray-200"
            >
              ดูงานของฉัน
            </Link>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-8 mt-20">
            <div className="bg-white p-8 rounded-2xl shadow-xl border border-gray-100 hover:shadow-2xl transition-all">
              <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-100 rounded-2xl mb-4">
                <Sparkles className="w-7 h-7 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                ตัดต่ออัตโนมัติ
              </h3>
              <p className="text-gray-600">
                AI วิเคราะห์และตัดช่วงเงียบ ใส่ซับไตเติ้ล และปรับสีให้อัตโนมัติ
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-xl border border-gray-100 hover:shadow-2xl transition-all">
              <div className="inline-flex items-center justify-center w-14 h-14 bg-purple-100 rounded-2xl mb-4">
                <Zap className="w-7 h-7 text-purple-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                รวดเร็ว
              </h3>
              <p className="text-gray-600">
                ประมวลผลเร็ว ได้วิดีโอภายในไม่กี่นาที พร้อมอัปโหลดเลย
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-xl border border-gray-100 hover:shadow-2xl transition-all">
              <div className="inline-flex items-center justify-center w-14 h-14 bg-pink-100 rounded-2xl mb-4">
                <Video className="w-7 h-7 text-pink-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                คุณภาพสูง
              </h3>
              <p className="text-gray-600">
                ซับไตเติ้ลสวย สีสดใส อัตราส่วน 9:16 พร้อมโพสต์
              </p>
            </div>
          </div>

          {/* How it works */}
          <div className="mt-24">
            <h2 className="text-4xl font-bold text-gray-900 mb-12">
              วิธีใช้งาน
            </h2>

            <div className="grid md:grid-cols-4 gap-6">
              {[
                { step: '1', title: 'อัปโหลดวิดีโอ', desc: 'เลือกวิดีโอที่ต้องการตัดต่อ' },
                { step: '2', title: 'AI วิเคราะห์', desc: 'ถอดเสียงและวิเคราะห์เนื้อหา' },
                { step: '3', title: 'ตัดต่ออัตโนมัติ', desc: 'ตัดช่วงเงียบ ใส่ซับ ปรับสี' },
                { step: '4', title: 'ดาวน์โหลด', desc: 'ได้วิดีโอพร้อมโพสต์' },
              ].map((item) => (
                <div key={item.step} className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 to-purple-600 text-white text-2xl font-bold rounded-full mb-4 shadow-lg">
                    {item.step}
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600 text-sm">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
