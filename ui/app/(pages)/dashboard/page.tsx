"use client";
import { useState } from "react";
import clsx from 'clsx'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/react'
import Link from "next/link";


function page() {
     const [active, setActive] = useState("720p");
     const [activeDuration, setActiveDuration] = useState("5s");
     const [selectedModel, setSelectedModel] = useState(null);
     const options = ["360p", "480p", "720p", "1080p"];
     const durationOptions = ["5s", "10s", "15s", "30s"];
     const [sidebarOpen, setSidebarOpen] = useState(false);

     const models = [
          { id: 1, name: 'Wan 2.5 Fast', icon: '/images/play-icon.svg', description: 'Fastest generation for quick drafts', badge: null },
          { id: 2, name: 'Higgsfield', icon: '/images/MagicWand.svg', description: 'Advanced camera controls and effect presets', badge: null },
          { id: 3, name: 'Minimax Hailuo', icon: '/images/VideoCamera.svg', description: 'High-dynamic, VFX-ready, fastest and most affordable', badge: null },
          { id: 4, name: 'OpenAI Sora 2', icon: '/images/Panorama.svg', description: 'Multi-shot video with sound generation', badge: null },
          { id: 5, name: 'Google Veo', icon: '/images/CheckCircle.svg', description: 'Precision video with sound control', badge: null },
          { id: 6, name: 'Wan', icon: '/images/play-icon.svg', description: 'Camera-controlled video with sound, more freedom', badge: null },
          { id: 7, name: 'Kling', icon: '/images/user-icon.svg', description: 'Perfect motion with advanced video control', badge: null },
          { id: 8, name: 'Seedance', icon: '/images/notepad-icon.svg', description: 'Cinematic, multi-shot video creation', badge: null },
     ];

     const [selected, setSelected] = useState(models[0]);

     return (
          <div className="font-inter bg-[url(/images/Pricing.png)] md:bg-top bg-center bg-no-repeat bg-cover">
               <section className="">
                    <div className={`fixed z-[999] 
    ${sidebarOpen ? "left-0" : "-left-full"} 
    lg:left-0 lg:top-[72px] top-auto lg:w-[301px] w-full flex flex-col justify-between 
    lg:h-[calc(100vh_-_72px)] h-[calc(100vh_-_68px)] lg:bottom-auto bottom-0 
    border-r border-gray-1300 py-8 px-4 sidebar-bg
    transition-all duration-300
  `}>
                         <div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Input Image</h3>
                                   <div className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-6 text-center">
                                        <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400">
                                             <img src="/images/image-icon.svg" alt="" />
                                             <div className="bg-gray-1500/[30%] flex items-center backdrop-blur-[8px] justify-center w-4 h-4 rounded-full absolute -top-2 -right-2">
                                                  <img src="/images/Plus.svg" alt="" />
                                             </div>
                                        </div>
                                        <h6 className="text-xs font-medium leading-[120%] text-white mt-2.5 mb-1">Upload Reference Image</h6>
                                        <p className="text-xs max-w-[177px] mx-auto font-normal leading-[120%] text-white/60">Add a photo of yourself or any image you want to animate.</p>
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Input Image</h3>
                                   <div className="rounded-lg border border-dashed border-gray-1100 bg-black-1000 p-6 text-center">
                                        <div className="w-8 h-8 mx-auto rounded-lg flex relative z-10 items-center justify-center bg-gray-1400">
                                             <img src="/images/VideoCamera.svg" alt="" />
                                             <div className="bg-gray-1500/[30%] flex items-center backdrop-blur-[8px] justify-center w-4 h-4 rounded-full absolute -top-2 -right-2">
                                                  <img src="/images/Plus.svg" alt="" />
                                             </div>
                                        </div>
                                        <h6 className="text-xs font-medium leading-[120%] text-white mt-2.5 mb-1">Upload a Video Motion Template</h6>
                                        <p className="text-xs max-w-[177px] mx-auto font-normal leading-[120%] text-white/60">Choose or upload a short clip to drive your animation.</p>
                                   </div>
                              </div>
                              <div className="mb-6">
                                   <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Resolution</h3>
                                   <div className="grid grid-cols-4 gap-1">
                                        {options.map((opt) => (
                                             <button
                                                  key={opt}
                                                  type="button"
                                                  onClick={() => setActive(opt)}
                                                  className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
            ${active === opt ? "bg-gray-1100/30! border-blue-1100!" : ""} 
          `}
                                             >
                                                  {opt}
                                             </button>
                                        ))}
                                   </div>
                                   <div className="mb-6 mt-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Duration</h3>
                                        <div className="grid grid-cols-4 gap-1">
                                             {durationOptions.map((duration) => (
                                                  <button
                                                       key={duration}
                                                       type="button"
                                                       onClick={() => setActiveDuration(duration)}
                                                       className={`text-[10px] font-medium border border-transparent leading-[120%] text-white h-[30px] flex items-center justify-center w-full bg-gray-1100/[20%] cursor-pointer rounded backdrop-blur-[8px]
                                                            ${activeDuration === duration ? "bg-gray-1100/30! border-blue-1100!" : ""} 
                                                       `}
                                                  >
                                                       {duration}
                                                  </button>
                                             ))}
                                        </div>
                                   </div>
                                   <div className="mb-6 mt-6">
                                        <h3 className="text-xs font-normal leading-[120%] text-white/60 mb-2">Model</h3>
                                        <Listbox value={selected} onChange={setSelected}>
                                             <ListboxButton
                                                  className={clsx(
                                                       'relative flex items-center justify-between w-full rounded-lg bg-gray-1600 py-2 px-3 text-left text-sm/6 text-white',
                                                       'focus:outline-none data-[focus]:outline-2 data-[focus]:-outline-offset-2 data-[focus]:outline-white/25'
                                                  )}
                                             >
                                                  <div className="flex items-center gap-2">
                                                       <img src={selected.icon} alt="" className="w-4 h-4" />
                                                       <span className="block truncate text-sm font-medium">{selected.name}</span>
                                                  </div>
                                                  <img src="/images/droparrow.svg" alt="" className="w-2.5 h-2.5 opacity-60" />
                                             </ListboxButton>

                                             <ListboxOptions
                                                  anchor="right start"
                                                  transition
                                                  className={clsx(
                                                       'w-[var(--button-width)] lg:w-[300px] lg:ml-2 rounded-xl border border-white/5 bg-[#1A1D24] p-1 focus:outline-none z-[9999]',
                                                       'transition duration-100 ease-in data-[leave]:data-[closed]:opacity-0'
                                                  )}
                                             >
                                                  {models.map((model) => (
                                                       <ListboxOption
                                                            key={model.id}
                                                            value={model}
                                                            className="group flex cursor-default items-center gap-3 rounded-lg py-2 px-3 select-none data-[focus]:bg-white/10"
                                                       >
                                                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white/5">
                                                                 <img src={model.icon} alt="" className="w-5 h-5" />
                                                            </div>
                                                            <div className="flex flex-col">
                                                                 <div className="flex items-center gap-2">
                                                                      <span className="text-sm font-medium text-white">{model.name}</span>
                                                                      {model.badge && (
                                                                           <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${model.badge.includes('Free') ? 'bg-orange-500/20 text-orange-400' :
                                                                                model.badge === 'Premium' ? 'bg-purple-500/20 text-purple-400' :
                                                                                     'bg-green-500/20 text-green-400'
                                                                                }`}>
                                                                                {model.badge}
                                                                           </span>
                                                                      )}
                                                                 </div>
                                                                 <span className="text-[10px] text-white/50 line-clamp-1">{model.description}</span>
                                                            </div>
                                                       </ListboxOption>
                                                  ))}
                                             </ListboxOptions>
                                        </Listbox>
                                   </div>
                              </div>
                         </div>
                         <div className="text-center">
                              <button onClick={() => setSidebarOpen(false)} className="md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300" >Generate for Free</button>
                         </div>
                    </div>
                    <div className="lg:w-[calc(100%_-_301px)] px-5 flex items-center justify-center flex-col md:pt-[160px] pt-[110px]  py-20 ml-auto min-h-screen">
                         <div className="text-center mb-6">
                              <div className="flex gap-2 items-center justify-center">
                                   <span className="text-[10px] font-medium text-black inline-block py-0.5 px-[7px] bg-blue-1000 rounded-xl">NEW</span>
                                   <h6 className="text-sm font-normal leading-[120%] text-gradient">Character Swap</h6>
                              </div>
                              <h2 className="md:text-5xl text-[38px] font-medium text-white leading-[120%] my-4 tracking-[-1px]">Turn Any Image Into Motion</h2>
                              <p className="md:text-base text-sm font-medium leading-[120%] text-white/60">Turn text, images, or videos into high-impact creative assets powered by the latest AI models.</p>
                              <div className="lg:hidden block mt-12">
                                   <button onClick={() => setSidebarOpen(true)} className="md:text-sm text-xs w-full text-center font-bold leading-[120%] text-black inline-block py-[11.5px] px-3.5 shadow-3xl bg1 rounded-xl hover:shadow-7xl transition-all duration-300" >Generate for Free</button>
                              </div>
                              <div className="flex items-center mt-20 w-fit mx-auto gap-2 py-2 px-3 rounded-full backdrop-blur-[4px] border border-gray-1700 tag-bg">
                                   <img src="/images/MagicWand2.svg" alt="" />
                                   <h6 className="text-sm font-normal leading-[120%] text-gradient">Generate in 3 easy steps</h6>
                              </div>
                         </div>
                         <div className="grid xl:grid-cols-3 md:grid-cols-2 md:max-w-[980px] max-w-full mx-auto gap-4">
                              <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                   <img src="/images/card-img7.png" alt="" />
                                   <div className="mt-2 py-4 px-2">
                                        <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                             <span className="text-white/60">01</span>    Upload an Image
                                        </h4>
                                        <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                             Choose a photo of you or any character
                                        </p>
                                   </div>
                              </div>
                              <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                   <img src="/images/card-img8.png" alt="" />
                                   <div className="mt-2 py-4 px-2">
                                        <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                             <span className="text-white/60">02</span>  Upload a Video Template
                                        </h4>
                                        <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                             Use a video to animate your image.
                                        </p>
                                   </div>
                              </div>
                              <div className="card-bg shadow-4xl rounded-2xl p-1.5 backdrop-blur-[4.69px] border border-transparent hover:border-blue-1100 hover:shadow-5xl transition-all ease-in-out duration-500">
                                   <img src="/images/card-img9.png" alt="" />
                                   <div className="mt-2 py-4 px-2">
                                        <h4 className="text-xl font-medium flex items-center gap-2 leading-[120%] text-white">
                                             <span className="text-white/60">03</span> Bring It to Life
                                        </h4>
                                        <p className="text-sm font-normal leading-[120%] text-white/60 mt-2">
                                             Become the character in the scene
                                        </p>
                                   </div>
                              </div>
                         </div>
                    </div>
               </section>
          </div>
     )
}

export default page
