document.addEventListener('DOMContentLoaded', function() {
    setupVoteButtons();
    setupMusicPlayer();
});


function setupVoteButtons() {
    var voteButtons = document.querySelectorAll('.vote-btn');
    
    for (var i = 0; i < voteButtons.length; i++) {
        var button = voteButtons[i];
        button.addEventListener('click', handleVoteClick);
    }
}


function handleVoteClick() {
    var button = this;
    var playlistId = button.dataset.id;
    var voteValue = parseInt(button.dataset.value);
    
    fetch('/vote/' + playlistId + '/' + voteValue, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        if (response.status === 401) {
            window.location.href = '/login';
            return null;
        }
        return response.json();
    })
    .then(function(data) {
        if (!data) return;
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        updateVoteDisplay(playlistId, data.vote_count, data.user_vote);
    })
    .catch(function(error) {
        console.error('Error voting:', error);
    });
}


function updateVoteDisplay(playlistId, voteCount, userVote) {
    var voteCountElements = document.querySelectorAll('[data-id="' + playlistId + '"].vote-count, [data-id="' + playlistId + '"].vote-count-large');
    
    for (var i = 0; i < voteCountElements.length; i++) {
        voteCountElements[i].textContent = voteCount;
    }
    
    var upvoteBtn = document.querySelector('.upvote[data-id="' + playlistId + '"]');
    var downvoteBtn = document.querySelector('.downvote[data-id="' + playlistId + '"]');
    
    if (upvoteBtn) {
        upvoteBtn.classList.remove('voted');
        if (userVote === 1) {
            upvoteBtn.classList.add('voted');
        }
    }
    
    if (downvoteBtn) {
        downvoteBtn.classList.remove('voted');
        if (userVote === -1) {
            downvoteBtn.classList.add('voted');
        }
    }
}


var currentSong = null;
var isPlaying = false;
var currentTime = 0;
var duration = 0;
var volume = 0.7;
var audioElement = null;
var currentGenre = null;

var playPauseBtn = null;
var progressFill = null;
var progressBar = null;
var currentTimeDisplay = null;
var totalTimeDisplay = null;
var volumeSlider = null;
var nowPlayingDisplay = null;
var songItems = null;


function setupMusicPlayer() {
    var musicPlayer = document.querySelector('.music-player');
    if (!musicPlayer) return;
    
    playPauseBtn = document.getElementById('play-pause-btn');
    progressFill = document.getElementById('progress-fill');
    progressBar = document.querySelector('.progress-bar');
    currentTimeDisplay = document.getElementById('current-time');
    totalTimeDisplay = document.getElementById('total-time');
    volumeSlider = document.getElementById('volume-slider');
    nowPlayingDisplay = document.getElementById('current-song');
    songItems = document.querySelectorAll('.song-item');
    
    createAudioElement();
    
    if (playPauseBtn) {
        playPauseBtn.addEventListener('click', togglePlay);
    }
    
    if (progressBar) {
        progressBar.addEventListener('click', seekToPosition);
    }
    
    if (volumeSlider) {
        volumeSlider.addEventListener('input', changeVolume);
    }
    
    for (var i = 0; i < songItems.length; i++) {
        songItems[i].addEventListener('click', handleSongClick);
    }
    
    for (var i = 0; i < songItems.length; i++) {
        var item = songItems[i];
        var song = item.dataset.song;
        var songInfo = parseSongTitle(song);
        console.log('Song:', song, '-> Artist:', songInfo.artist, 'Song Title:', songInfo.song);
        var songInfoDiv = item.querySelector('.song-info');
        if (songInfoDiv) {
            songInfoDiv.innerHTML = '<span style="color: #1db954;">' + songInfo.song + '</span>&nbsp;- ' + songInfo.artist;
        }
    }
}


function createAudioElement() {
    audioElement = document.createElement('audio');
    audioElement.preload = 'metadata';
    audioElement.volume = volume;
    
    audioElement.addEventListener('loadedmetadata', function() {
        duration = audioElement.duration;
        updateProgressBar();
    });
    
    audioElement.addEventListener('timeupdate', function() {
        if (isPlaying) {
            currentTime = audioElement.currentTime;
            updateProgressBar();
        }
    });
    
    audioElement.addEventListener('ended', function() {
        pauseSong();
        currentTime = 0;
        updateProgressBar();
    });
    
    audioElement.addEventListener('error', function() {
        alert('Error loading audio file. Please check if the file exists.');
    });
    
    document.body.appendChild(audioElement);
}


function handleSongClick() {
    var songName = this.dataset.song;
    currentGenre = this.dataset.genre;
    
    if (currentSong === songName) {
        togglePlay();
    } else {
        selectSong(songName);
        playSong();
    }
}


function selectSong(songName) {
    currentSong = songName;
    
    for (var i = 0; i < songItems.length; i++) {
        songItems[i].classList.remove('playing');
    }
    
    currentTime = 0;
    updateProgressBar();
}


function togglePlay() {
    if (!currentSong) {
        var firstSong = document.querySelector('.song-item');
        if (firstSong) {
            currentGenre = firstSong.dataset.genre;
            selectSong(firstSong.dataset.song);
        } else {
            return;
        }
    }
    
    if (isPlaying) {
        pauseSong();
    } else {
        playSong();
    }
}


function playSong() {
    if (!currentSong) return;
    
    isPlaying = true;
    playPauseBtn.textContent = 'Pause';
    playPauseBtn.classList.add('playing');
    
    var songInfo = parseSongTitle(currentSong);
    nowPlayingDisplay.textContent = 'Now playing: ' + songInfo.song + ' - ' + songInfo.artist;
    
    var currentItem = document.querySelector('[data-song="' + currentSong + '"]');
    if (currentItem) {
        currentItem.classList.add('playing');
    }
    
    var audioFile = getAudioFilePath(currentSong, currentGenre);
    console.log('Audio file path:', audioFile);
    
    if (audioElement.src !== window.location.origin + audioFile) {
        audioElement.src = audioFile;
        audioElement.load();
    }
    
    audioElement.currentTime = currentTime;
    
    audioElement.play().catch(function(error) {
        if (error.name === 'NotAllowedError') {
            alert('Click anywhere on the page first to enable audio playback');
        } else {
            alert('Error playing audio: ' + error.message);
        }
        pauseSong();
    });
}


function pauseSong() {
    isPlaying = false;
    playPauseBtn.textContent = 'Play';
    playPauseBtn.classList.remove('playing');
    
    nowPlayingDisplay.textContent = 'Select a song to play';
    
    var currentItem = document.querySelector('[data-song="' + currentSong + '"]');
    if (currentItem) {
        currentItem.classList.remove('playing');
    }
    
    if (audioElement) {
        audioElement.pause();
    }
}


function updateProgressBar() {
    var progress = 0;
    if (duration > 0) {
        progress = (currentTime / duration) * 100;
    }
    
    progressFill.style.width = progress + '%';
    currentTimeDisplay.textContent = formatTime(currentTime);
    totalTimeDisplay.textContent = formatTime(duration);
}


function seekToPosition(event) {
    var rect = progressBar.getBoundingClientRect();
    var clickX = event.clientX - rect.left;
    var percentage = clickX / rect.width;
    var seekTime = percentage * duration;
    
    currentTime = seekTime;
    
    if (audioElement) {
        audioElement.currentTime = seekTime;
    }
    
    updateProgressBar();
}


function changeVolume(event) {
    volume = event.target.value;
    
    if (audioElement) {
        audioElement.volume = volume;
    }
}


function formatTime(seconds) {
    var mins = Math.floor(seconds / 60);
    var secs = Math.floor(seconds % 60);
    
    if (secs < 10) {
        secs = '0' + secs;
    }
    
    return mins + ':' + secs;
}


function parseSongTitle(fullTitle) {
    var lastDash = fullTitle.lastIndexOf(' - ');
    
    if (lastDash > 0) {
        var artist = fullTitle.substring(0, lastDash).trim();
        var song = fullTitle.substring(lastDash + 3).trim();
        return { artist: artist, song: song };
    }
    
    return { artist: 'Unknown Artist', song: fullTitle.trim() };
}


function getAudioFilePath(songTitle, genre) {
    var songInfo = parseSongTitle(songTitle);
    var fileName = songInfo.artist + ' - ' + songInfo.song;
    fileName = fileName.replace(/[<>:"/\\|?*]/g, '');
    
    var genreFolder = genre.toLowerCase().replace(/[^a-z0-9]/g, '');
    
    return '/static/audio/' + genreFolder + '/' + fileName + '.mp3';
}

function toggleEditForm(commentId) {
    var form = document.getElementById('edit-form-' + commentId);
    if (form.style.display === 'none') {
        form.style.display = 'block';
        form.querySelector('textarea').focus();
    } else {
        form.style.display = 'none';
    }
}