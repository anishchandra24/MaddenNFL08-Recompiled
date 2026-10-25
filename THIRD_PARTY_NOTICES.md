# Third-party notices

This project builds on the software below. Their licenses apply to their code.

## ReXGlue SDK (BSD 3-Clause)

https://github.com/rexglue/rexglue-sdk

The patches in this repository modify files from the ReXGlue SDK, and the build uses the SDK at version 0.10.0: patches/codegen_vector_alias.patch changes src/codegen/builders/vector.cpp, and patches/texture_mip_layout.patch changes src/graphics/pipeline/texture/util.cpp and include/rex/graphics/pipeline/texture/util.h. The SDK's license text, copied unchanged:

    Copyright (c) 2026, Tom Clay <tomc@tctechstuff.com>
    
    Portions of this software are derived from the Xenia project:
    Copyright (c) 2022, Ben Vanik and Xenia project contributors
    https://xenia.jp
    
    All rights reserved.
    
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
    
    1. Redistributions of source code must retain the above copyright notice, this
       list of conditions and the following disclaimer.
    
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.
    
    3. Neither the name of the copyright holder nor the names of its
       contributors may be used to endorse or promote products derived from
       this software without specific prior written permission.
    
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
    FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
    OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    

## Xenia (BSD 3-Clause)

https://github.com/xenia-project/xenia

Parts of the ReXGlue SDK are derived from Xenia. The SDK license text above carries its copyright notice.

## Xenia Canary (BSD 3-Clause)

https://github.com/xenia-canary/xenia-canary

patches/texture_mip_layout.patch is a port, to the ReXGlue SDK's code, of changes from Xenia Canary pull request #1243 "Misc guest texture layout edge cases" by goldislead (https://github.com/xenia-canary/xenia-canary/pull/1243). Xenia Canary is a fork of Xenia and uses the same BSD 3-Clause license; see the Xenia repository for its copyright notice.
